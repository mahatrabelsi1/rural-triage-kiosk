from __future__ import annotations

import io
import logging
import re
import wave
from functools import lru_cache

import numpy as np
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from src import config
from src.triage.schemas import TranscriptionResponse

try:
    from transformers import pipeline
except Exception:  # pragma: no cover - handled at runtime when dependency is absent
    pipeline = None

logger = logging.getLogger(__name__)

router = APIRouter()

TTS_MODEL_NAME = config.TTS_MODEL_NAME
STT_MODEL_NAME = config.STT_MODEL_NAME
STT_SAMPLE_RATE = 16000
# 16 kHz mono 16-bit is ~32 KB/s, so this allows about 60 seconds of speech.
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
# Below this RMS level the clip is treated as silence (Whisper invents text on silence).
SILENCE_RMS = 0.004
_HAS_WORD = re.compile(r"\w", re.UNICODE)


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=800)


@lru_cache(maxsize=1)
def get_tts_pipeline():
    """Load the TTS model once; return None (and stay None) if it can't load."""
    if pipeline is None:
        return None
    try:
        return pipeline("text-to-speech", model=TTS_MODEL_NAME)
    except Exception:
        logger.warning("TTS model %s unavailable; frontend will use browser voice.", TTS_MODEL_NAME, exc_info=True)
        return None


def _audio_to_wav_bytes(audio, sampling_rate: int) -> bytes:
    values = audio
    if hasattr(values, "detach"):
        values = values.detach().cpu().numpy()
    samples = np.clip(np.asarray(values, dtype=np.float32).reshape(-1), -1.0, 1.0)
    pcm = (samples * 32767).astype("<i2").tobytes()

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(int(sampling_rate))
        wav.writeframes(pcm)
    return output.getvalue()


@router.post("")
def synthesize_speech(req: SpeechRequest):
    tts_pipeline = get_tts_pipeline()
    if tts_pipeline is None:
        raise HTTPException(status_code=503, detail="Text-to-speech model is not available.")

    try:
        result = tts_pipeline(req.text.strip())
        wav_bytes = _audio_to_wav_bytes(result["audio"], int(result["sampling_rate"]))
    except Exception as exc:
        logger.warning("TTS synthesis failed.", exc_info=True)
        raise HTTPException(status_code=503, detail="Text-to-speech failed.") from exc

    return Response(content=wav_bytes, media_type="audio/wav")


@lru_cache(maxsize=1)
def get_stt_pipeline():
    """Load the speech-to-text model once; None if it can't load (e.g. offline
    on first run). Browser speech recognition is tried before this."""
    if pipeline is None:
        return None
    try:
        return pipeline("automatic-speech-recognition", model=STT_MODEL_NAME)
    except Exception:
        logger.warning("STT model %s unavailable.", STT_MODEL_NAME, exc_info=True)
        return None


def wav_bytes_to_mono_16k(data: bytes) -> np.ndarray:
    """Decode a PCM WAV upload into float32 mono samples at 16 kHz.

    Only uncompressed PCM is accepted so no ffmpeg is needed on the kiosk; the
    frontend records straight to WAV.
    """
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError) as exc:
        raise ValueError("Audio must be a PCM WAV file.") from exc

    if width == 2:
        samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 1:
        samples = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 4:
        samples = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError("Unsupported WAV sample width.")

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    if rate != STT_SAMPLE_RATE and samples.size:
        duration = samples.size / rate
        target = np.linspace(0, samples.size - 1, int(duration * STT_SAMPLE_RATE))
        samples = np.interp(target, np.arange(samples.size), samples).astype(np.float32)

    return samples


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_speech(request: Request):
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Recording is too long. Please speak for under a minute.")
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="No audio received.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Recording is too long. Please speak for under a minute.")

    try:
        samples = wav_bytes_to_mono_16k(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if samples.size < STT_SAMPLE_RATE // 4 or float(np.sqrt(np.mean(samples**2))) < SILENCE_RMS:
        return TranscriptionResponse(text="")

    stt_pipeline = await run_in_threadpool(get_stt_pipeline)
    if stt_pipeline is None:
        raise HTTPException(status_code=503, detail="Speech-to-text model is not available.")

    try:
        result = await run_in_threadpool(
            stt_pipeline,
            {"raw": samples, "sampling_rate": STT_SAMPLE_RATE},
            generate_kwargs=_generate_kwargs(),
        )
    except Exception as exc:
        logger.warning("Speech-to-text failed.", exc_info=True)
        raise HTTPException(status_code=503, detail="Speech-to-text failed.") from exc

    return TranscriptionResponse(text=clean_transcript(str(result.get("text", ""))))


def _generate_kwargs() -> dict:
    kwargs = {"task": "transcribe", "max_new_tokens": 120}
    if config.STT_LANGUAGE:
        kwargs["language"] = config.STT_LANGUAGE
    return kwargs


def clean_transcript(text: str) -> str:
    """Drop Whisper's non-speech hallucinations ("....", "♪") and collapse
    runs of repeated punctuation."""
    cleaned = re.sub(r"([.!?,])\1{2,}", r"\1", text).strip()
    return cleaned if _HAS_WORD.search(cleaned) else ""
