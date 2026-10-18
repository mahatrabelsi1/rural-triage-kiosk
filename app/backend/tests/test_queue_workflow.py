"""Staff queue workflow: mark a patient as seen, move to the next one."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from helpers import TempDbMixin
from src.main import app
from src.storage import db as storage_db


class QueueWorkflowTest(TempDbMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        env = patch.dict(os.environ, {"STAFF_ACCOUNTS": "nurse:nurse2026:Nurse Amal,doctor:doctor2026:Dr. Karim"})
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(app)

    def headers(self, username="nurse", password="nurse2026"):
        token = self.client.post("/auth/login", json={"username": username, "password": password}).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    def submit(self, name, symptoms, **extra):
        payload = {"patient_name": name, "symptoms": symptoms, "use_nlp_extraction": False, **extra}
        res = self.client.post("/triage", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    def backdate(self, session_id, minutes):
        with storage_db.get_conn() as conn:
            conn.execute(
                "UPDATE triage_logs SET created_at = datetime('now', ?) WHERE session_id = ?",
                (f"-{minutes} minutes", session_id),
            )

    def queue(self, status="waiting", headers=None):
        res = self.client.get(f"/triage?status={status}", headers=headers or self.headers())
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()


class TestMarkSeen(QueueWorkflowTest):
    def test_mark_done_moves_patient_out_of_waiting(self):
        first = self.submit("Amina", {"chest_pain": 3})
        self.submit("Youssef", {"fever": 2})
        headers = self.headers()

        res = self.client.post(f"/triage/{first['session_id']}/complete", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["updated_by"], "Nurse Amal")

        waiting = [q["patient_name"] for q in self.queue("waiting", headers)]
        done = self.queue("done", headers)
        self.assertEqual(waiting, ["Youssef"])
        self.assertEqual([q["patient_name"] for q in done], ["Amina"])
        self.assertEqual(done[0]["status"], "done")
        self.assertEqual(done[0]["completed_by"], "Nurse Amal")
        self.assertTrue(done[0]["completed_at"])

    def test_session_detail_shows_who_marked_it(self):
        sid = self.submit("Amina", {"fever": 1})["session_id"]
        headers = self.headers("doctor", "doctor2026")
        self.assertEqual(self.client.get(f"/triage/{sid}", headers=headers).json()["status"], "waiting")
        self.client.post(f"/triage/{sid}/complete", headers=headers)
        log = self.client.get(f"/triage/{sid}", headers=headers).json()
        self.assertEqual(log["status"], "done")
        self.assertEqual(log["completed_by"], "Dr. Karim")

    def test_reopen_returns_patient_to_waiting(self):
        sid = self.submit("Amina", {"fever": 1})["session_id"]
        headers = self.headers()
        self.client.post(f"/triage/{sid}/complete", headers=headers)
        res = self.client.post(f"/triage/{sid}/reopen", headers=headers)
        self.assertEqual(res.json()["status"], "waiting")
        waiting = self.queue("waiting", headers)
        self.assertEqual([q["session_id"] for q in waiting], [sid])
        self.assertIsNone(waiting[0]["completed_by"])

    def test_requires_staff_login(self):
        sid = self.submit("Amina", {"fever": 1})["session_id"]
        self.assertEqual(self.client.post(f"/triage/{sid}/complete").status_code, 401)
        self.assertEqual(self.client.post(f"/triage/{sid}/reopen").status_code, 401)

    def test_unknown_or_invalid_session(self):
        headers = self.headers()
        self.assertEqual(self.client.post("/triage/0123456789ab/complete", headers=headers).status_code, 404)
        self.assertEqual(self.client.post("/triage/not-valid/complete", headers=headers).status_code, 422)


class TestQueueOrder(QueueWorkflowTest):
    def test_most_urgent_first_then_longest_waiting(self):
        late_red = self.submit("Late Red", {"chest_pain": 3})["session_id"]
        early_green = self.submit("Early Green", {"cough": 1})["session_id"]
        early_red = self.submit("Early Red", {"bleeding": 3})["session_id"]
        orange = self.submit("Orange", {"fever": 2})["session_id"]
        self.backdate(early_red, 30)
        self.backdate(early_green, 40)
        self.backdate(orange, 10)
        self.backdate(late_red, 5)

        names = [q["patient_name"] for q in self.queue()]
        self.assertEqual(names, ["Early Red", "Late Red", "Orange", "Early Green"])

    def test_seen_list_is_most_recent_first(self):
        a = self.submit("A", {"fever": 1})["session_id"]
        b = self.submit("B", {"fever": 1})["session_id"]
        headers = self.headers()
        self.client.post(f"/triage/{a}/complete", headers=headers)
        with storage_db.get_conn() as conn:
            conn.execute("UPDATE session_status SET updated_at = datetime('now', '-5 minutes') WHERE session_id = ?", (a,))
        self.client.post(f"/triage/{b}/complete", headers=headers)
        self.assertEqual([q["patient_name"] for q in self.queue("done", headers)], ["B", "A"])

    def test_seen_order_holds_within_the_same_second(self):
        # "Done, Next Patient" clicked quickly: several patients marked in one second.
        ids = [self.submit(name, {"fever": 1})["session_id"] for name in ("P1", "P2", "P3", "P4")]
        headers = self.headers()
        for sid in ids:
            self.client.post(f"/triage/{sid}/complete", headers=headers)
        self.assertEqual([q["patient_name"] for q in self.queue("done", headers)], ["P4", "P3", "P2", "P1"])


class TestClarificationKeepsOneEntry(QueueWorkflowTest):
    VAGUE = "I feel very bad but I cannot explain clearly"

    def test_answers_reuse_the_same_session(self):
        first = self.submit("Val", {}, chief_complaint_text=self.VAGUE, use_nlp_extraction=True)
        self.assertTrue(first["needs_clarification"])

        second = self.submit(
            "Val", {"chest_pain": 3}, chief_complaint_text=self.VAGUE,
            clarification_completed=True, session_id=first["session_id"],
        )
        self.assertEqual(second["session_id"], first["session_id"])

        queue = self.queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["triage_level"], "RED")

    def test_cannot_overwrite_a_finished_or_unrelated_session(self):
        normal = self.submit("Other", {"fever": 2})  # did not ask for clarification
        res = self.submit("Intruder", {}, clarification_completed=True, session_id=normal["session_id"])
        self.assertNotEqual(res["session_id"], normal["session_id"])

        vague = self.submit("Val", {}, chief_complaint_text=self.VAGUE, use_nlp_extraction=True)
        self.client.post(f"/triage/{vague['session_id']}/complete", headers=self.headers())
        res = self.submit("Val", {"fever": 1}, clarification_completed=True, session_id=vague["session_id"])
        self.assertNotEqual(res["session_id"], vague["session_id"])


if __name__ == "__main__":
    unittest.main()
