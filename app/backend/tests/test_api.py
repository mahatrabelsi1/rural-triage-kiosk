"""End-to-end API tests through FastAPI's TestClient."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from helpers import TempDbMixin
from src import auth
from src.main import app
from src.nlp import hf_extractor


def _raise(*_args, **_kwargs):
    raise OSError("We couldn't connect to 'https://huggingface.co'")


class ApiTestCase(TempDbMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Pin the demo accounts so a local .env with real passwords can't break tests.
        env = patch.dict(os.environ, {"STAFF_ACCOUNTS": "nurse:nurse2026:Nurse,doctor:doctor2026:Doctor"})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(app)

    def login(self, username="nurse", password="nurse2026"):
        return self.client.post("/auth/login", json={"username": username, "password": password})

    def staff_headers(self):
        return {"Authorization": f"Bearer {self.login().json()['token']}"}

    def submit(self, **overrides):
        payload = {"chief_complaint_text": "fever and cough", "symptoms": {"fever": 2}, "use_nlp_extraction": False}
        payload.update(overrides)
        return self.client.post("/triage", json=payload)


class TestAuth(ApiTestCase):
    def test_demo_accounts_can_log_in(self):
        for username, password in [("nurse", "nurse2026"), ("doctor", "doctor2026")]:
            res = self.login(username, password)
            self.assertEqual(res.status_code, 200, username)
            self.assertTrue(res.json()["token"])

    def test_wrong_password_rejected(self):
        self.assertEqual(self.login("nurse", "wrong").status_code, 401)
        self.assertEqual(self.login("nobody", "nurse2026").status_code, 401)

    def test_me_requires_valid_token(self):
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        self.assertEqual(self.client.get("/auth/me", headers={"Authorization": "Bearer junk"}).status_code, 401)
        self.assertEqual(self.client.get("/auth/me", headers=self.staff_headers()).json()["username"], "nurse")

    def test_tampered_token_rejected(self):
        token = self.login().json()["token"]
        body, sig = token.split(".")
        self.assertIsNone(auth.verify_token(body + "x." + sig))

    def test_expired_token_rejected(self):
        account = {"username": "nurse", "display_name": "Nurse"}
        token, _ = auth.issue_token(account, ttl_minutes=-1)
        self.assertIsNone(auth.verify_token(token))


class TestProtectedEndpoints(ApiTestCase):
    def test_intake_does_not_need_login(self):
        res = self.submit(entered_by="companion")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["triage_level"], "ORANGE")

    def test_queue_and_session_need_login(self):
        session_id = self.submit().json()["session_id"]
        self.assertEqual(self.client.get("/triage").status_code, 401)
        self.assertEqual(self.client.get(f"/triage/{session_id}").status_code, 401)

        headers = self.staff_headers()
        queue = self.client.get("/triage", headers=headers).json()
        self.assertEqual(queue[0]["session_id"], session_id)
        self.assertEqual(self.client.get(f"/triage/{session_id}", headers=headers).status_code, 200)

    def test_invalid_rating_returns_422(self):
        self.assertEqual(self.submit(symptoms={"fever": 5}).status_code, 422)
        self.assertEqual(self.submit(symptoms={"made_up": 1}).status_code, 422)


class TestCors(ApiTestCase):
    def preflight(self, origin):
        return self.client.options(
            "/speech/transcribe",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
        )

    def test_local_frontend_on_any_port_is_allowed(self):
        # Vite moves to 5174 when 5173 is busy; that used to fail with 400.
        for origin in ["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5175", "http://[::1]:5173"]:
            res = self.preflight(origin)
            self.assertEqual(res.status_code, 200, origin)
            self.assertEqual(res.headers["access-control-allow-origin"], origin)

    def test_other_sites_are_rejected(self):
        for origin in ["http://evil.example.com", "http://localhost.evil.com:5173"]:
            self.assertEqual(self.preflight(origin).status_code, 400, origin)


class TestPdf(ApiTestCase):
    def test_pdf_built_from_stored_session(self):
        session_id = self.submit(patient_name="Amina").json()["session_id"]
        self.assertEqual(self.client.get(f"/pdf/{session_id}").status_code, 401)

        res = self.client.get(f"/pdf/{session_id}", headers=self.staff_headers())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))

    def test_pdf_unknown_session_404(self):
        self.assertEqual(self.client.get("/pdf/0123456789ab", headers=self.staff_headers()).status_code, 404)

    def test_pdf_rejects_path_traversal_ids(self):
        headers = self.staff_headers()
        for bad in ["..%2F..%2Fevil", "not-a-session", "ABCDEF123456"]:
            self.assertIn(self.client.get(f"/pdf/{bad}", headers=headers).status_code, {404, 422}, bad)


class TestOfflineFallbacks(ApiTestCase):
    def test_triage_survives_ner_model_download_failure(self):
        hf_extractor.get_ner_pipeline.cache_clear()
        try:
            with patch.object(hf_extractor, "pipeline", side_effect=_raise), self.assertLogs("src.nlp.hf_extractor", "WARNING"):
                res = self.submit(chief_complaint_text="severe chest pain", use_nlp_extraction=True, symptoms={})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["triage_level"], "RED")
            self.assertEqual(res.json()["extracted_entities"], [])
        finally:
            hf_extractor.get_ner_pipeline.cache_clear()

    def test_speech_returns_503_when_model_unavailable(self):
        from src.api import routes_speech

        routes_speech.get_tts_pipeline.cache_clear()
        try:
            with patch.object(routes_speech, "pipeline", side_effect=_raise), self.assertLogs("src.api.routes_speech", "WARNING"):
                res = self.client.post("/speech", json={"text": "hello"})
            self.assertEqual(res.status_code, 503)
        finally:
            routes_speech.get_tts_pipeline.cache_clear()


if __name__ == "__main__":
    unittest.main()
