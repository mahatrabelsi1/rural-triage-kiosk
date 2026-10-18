import io
import unittest
import wave
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from helpers import TempDbMixin
from src.api import routes_speech
from src.main import app


def make_wav(seconds=1.0, rate=8000, channels=1):
    t = np.linspace(0, seconds, int(seconds * rate), endpoint=False)
    tone = (0.3 * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    if channels == 2:
        tone = np.repeat(tone, 2)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(tone.tobytes())
    return buf.getvalue()


class TestWavDecoding(unittest.TestCase):
    def test_resamples_to_16k_mono(self):
        samples = routes_speech.wav_bytes_to_mono_16k(make_wav(seconds=1.0, rate=8000, channels=2))
        self.assertEqual(samples.dtype, np.float32)
        self.assertAlmostEqual(samples.size, 16000, delta=2)
        self.assertLessEqual(float(np.abs(samples).max()), 1.0)

    def test_rejects_non_wav(self):
        with self.assertRaises(ValueError):
            routes_speech.wav_bytes_to_mono_16k(b"definitely not audio")


class TestTranscribeEndpoint(TempDbMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.client = TestClient(app)
        routes_speech.get_stt_pipeline.cache_clear()
        self.addCleanup(routes_speech.get_stt_pipeline.cache_clear)

    def post(self, data):
        return self.client.post("/speech/transcribe", content=data, headers={"Content-Type": "audio/wav"})

    def test_transcribes_with_model(self):
        calls = []

        def fake_model(inputs, **kwargs):
            calls.append(inputs)
            return {"text": " I have a headache "}

        with patch.object(routes_speech, "get_stt_pipeline", return_value=fake_model):
            res = self.post(make_wav())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["text"], "I have a headache")
        self.assertEqual(calls[0]["sampling_rate"], 16000)

    def test_bad_audio_is_400(self):
        self.assertEqual(self.post(b"nope").status_code, 400)
        self.assertEqual(self.post(b"").status_code, 400)

    def test_too_long_is_413(self):
        self.assertEqual(self.post(b"0" * (routes_speech.MAX_UPLOAD_BYTES + 1)).status_code, 413)

    def test_model_unavailable_is_503(self):
        with patch.object(routes_speech, "get_stt_pipeline", return_value=None):
            self.assertEqual(self.post(make_wav()).status_code, 503)

    def test_silence_skips_model(self):
        quiet = np.zeros(16000).astype("<i2").tobytes()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(quiet)
        with patch.object(routes_speech, "get_stt_pipeline", side_effect=AssertionError("should not load")):
            self.assertEqual(self.post(buf.getvalue()).json()["text"], "")

    def test_hallucinated_punctuation_is_dropped(self):
        self.assertEqual(routes_speech.clean_transcript(" ............ "), "")
        self.assertEqual(routes_speech.clean_transcript("I have a fever..."), "I have a fever.")
        self.assertEqual(routes_speech.clean_transcript("عندي حمى"), "عندي حمى")

    def test_tiny_clip_returns_empty_text_without_model(self):
        with patch.object(routes_speech, "get_stt_pipeline", side_effect=AssertionError("should not load")):
            res = self.post(make_wav(seconds=0.1))
        self.assertEqual(res.json()["text"], "")


if __name__ == "__main__":
    unittest.main()
