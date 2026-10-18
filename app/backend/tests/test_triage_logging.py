import sys
import unittest
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from helpers import TempDbMixin  # noqa: E402
from src.api import routes_triage  # noqa: E402
from src.triage.schemas import IntakeRequest  # noqa: E402


class TestTriageLogging(TempDbMixin, unittest.TestCase):
    def test_triage_request_is_logged_and_retrievable(self):
        req = IntakeRequest(
            patient_name="Alice",
            chief_complaint_text="I have fever and cough",
            symptoms={"fever": 2, "cough": 1, "chest_pain": 0},
            use_nlp_extraction=True,
        )

        triage_response = routes_triage.triage(req)
        log = routes_triage.get_triage_log(triage_response.session_id)

        self.assertEqual(log["session_id"], triage_response.session_id)
        self.assertEqual(log["triage_level"], triage_response.triage_level)
        self.assertEqual(log["request_payload"]["patient_name"], "Alice")
        self.assertEqual(log["response_payload"]["session_id"], triage_response.session_id)
        self.assertIn("created_at", log)

    def test_unknown_session_returns_404(self):
        with self.assertRaises(HTTPException) as ctx:
            routes_triage.get_triage_log("not-found")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_recent_queue_is_sorted_by_urgency(self):
        green = IntakeRequest(
            patient_name="Green",
            chief_complaint_text="routine check",
            symptoms={},
            use_nlp_extraction=False,
        )
        red = IntakeRequest(
            patient_name="Red",
            chief_complaint_text="severe chest pain",
            symptoms={"chest_pain": 3},
            use_nlp_extraction=False,
        )
        orange = IntakeRequest(
            patient_name="Orange",
            chief_complaint_text="fever",
            symptoms={"fever": 2},
            use_nlp_extraction=False,
        )

        routes_triage.triage(green)
        routes_triage.triage(red)
        routes_triage.triage(orange)

        queue = routes_triage.recent_triage_queue()

        self.assertEqual([item["triage_level"] for item in queue[:3]], ["RED", "ORANGE", "GREEN"])
        self.assertEqual(queue[0]["patient_name"], "Red")


if __name__ == "__main__":
    unittest.main()
