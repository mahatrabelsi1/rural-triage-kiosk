import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api import routes_triage  # noqa: E402
from src.storage import db as storage_db  # noqa: E402
from src.triage.schemas import IntakeRequest  # noqa: E402


class TestTriageSafety(unittest.TestCase):
    def setUp(self):
        self.original_db_path = storage_db.DB_PATH
        self.test_db_path = ROOT / "outputs" / f"test_triage_safety_{uuid.uuid4().hex}.db"
        self.test_db_path.parent.mkdir(parents=True, exist_ok=True)
        storage_db.DB_PATH = self.test_db_path
        storage_db.init_db()

    def tearDown(self):
        storage_db.DB_PATH = self.original_db_path

    def test_critical_distress_text_forces_red(self):
        req = IntakeRequest(
            patient_name="maha",
            chief_complaint_text="im gonna die",
            symptoms={},
            use_nlp_extraction=True,
        )

        res = routes_triage.triage(req)
        self.assertEqual(res.triage_level, "RED")
        self.assertTrue(any(m.id == "S1" for m in res.matched_rules))

    def test_critical_distress_typo_variant_forces_red(self):
        req = IntakeRequest(
            patient_name="maha",
            chief_complaint_text="im ganna die",
            symptoms={},
            use_nlp_extraction=True,
        )

        res = routes_triage.triage(req)
        self.assertEqual(res.triage_level, "RED")
        self.assertTrue(any(m.id == "S1" for m in res.matched_rules))

    def test_low_confidence_empty_symptoms_triggers_clarification(self):
        req = IntakeRequest(
            patient_name="maha",
            chief_complaint_text="I feel very bad but I cannot explain clearly",
            symptoms={},
            use_nlp_extraction=True,
        )

        res = routes_triage.triage(req)
        self.assertTrue(res.needs_clarification)
        self.assertGreaterEqual(len(res.follow_up_questions), 1)

    def test_clarification_completed_disables_follow_up_questions(self):
        req = IntakeRequest(
            patient_name="maha",
            chief_complaint_text="I feel very bad but I cannot explain clearly",
            symptoms={},
            use_nlp_extraction=True,
            clarification_completed=True,
        )

        res = routes_triage.triage(req)
        self.assertFalse(res.needs_clarification)
        self.assertEqual(len(res.follow_up_questions), 0)


if __name__ == "__main__":
    unittest.main()
