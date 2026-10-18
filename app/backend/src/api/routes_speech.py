from __future__ import annotations

import io
import logging
import wave
from functools import lru_cache

import numpy as np
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from src import config

try:
    from transformers import pipeline
except Exception:  # pragma: no cover - handled at runtime when dependency is absent
    pipeline = None

logger = logging.getLogger(__name__)

router = APIRouter()

TTS_MODEL_NAME = config.TTS_MODEL_NAME


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
