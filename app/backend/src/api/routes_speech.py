from __future__ import annotations

import io
import os
import wave
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

try:
    from transformers import pipeline
except Exception:  # pragma: no cover - handled at runtime when dependency is absent
    pipeline = None

router = APIRouter()

TTS_MODEL_NAME = os.getenv("TTS_MODEL_NAME", "Vedika35/Vedika_text_to_speech")


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=800)


@lru_cache(maxsize=1)
def get_tts_pipeline():
    if pipeline is None:
        return None
    return pipeline("text-to-speech", model=TTS_MODEL_NAME)


def _audio_to_wav_bytes(audio, sampling_rate: int) -> bytes:
    values = audio
    if hasattr(values, "detach"):
        values = values.detach().cpu().numpy()
    elif hasattr(values, "numpy"):
        values = values.numpy()

    if hasattr(values, "reshape"):
        values = values.reshape(-1)
    else:
        values = list(values)

    pcm = bytearray()
    for sample in values:
        clipped = max(-1.0, min(1.0, float(sample)))
        pcm.extend(int(clipped * 32767).to_bytes(2, byteorder="little", signed=True))

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(int(sampling_rate))
        wav.writeframes(bytes(pcm))
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
        raise HTTPException(status_code=503, detail=f"Text-to-speech failed: {exc}") from exc

    return Response(content=wav_bytes, media_type="audio/wav")
