import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from helpers import TempDbMixin  # noqa: E402
from src.api import routes_triage  # noqa: E402
from src.triage.schemas import IntakeRequest  # noqa: E402


class TestTriageSafety(TempDbMixin, unittest.TestCase):
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

    def test_elderly_high_risk_symptom_escalates_to_orange(self):
        req = IntakeRequest(
            patient_name="maha",
            age_group="elderly",
            chief_complaint_text="mild chest discomfort",
            symptoms={"chest_pain": 1},
            use_nlp_extraction=False,
        )

        res = routes_triage.triage(req)
        self.assertEqual(res.triage_level, "ORANGE")
        self.assertTrue(any(m.id == "RF3" for m in res.matched_rules))

    def test_diabetes_with_severe_dehydration_escalates_to_red(self):
        req = IntakeRequest(
            patient_name="maha",
            chief_complaint_text="very weak and dehydrated",
            symptoms={"dehydration_signs": 3},
            chronic_illnesses=["diabetes"],
            use_nlp_extraction=False,
        )

        res = routes_triage.triage(req)
        self.assertEqual(res.triage_level, "RED")
        self.assertTrue(any(m.id == "RF4" for m in res.matched_rules))

    def test_heart_problem_with_chest_pain_escalates_to_orange(self):
        req = IntakeRequest(
            patient_name="maha",
            chief_complaint_text="chest pain",
            symptoms={"chest_pain": 1},
            chronic_illnesses=["heart_problem"],
            use_nlp_extraction=False,
        )

        res = routes_triage.triage(req)
        self.assertEqual(res.triage_level, "ORANGE")
        self.assertTrue(any(m.id == "RF7" for m in res.matched_rules))

    def test_pregnancy_bleeding_risk_factor_forces_red(self):
        req = IntakeRequest(
            patient_name="maha",
            chief_complaint_text="bleeding during pregnancy",
            symptoms={"pregnancy_bleeding": 1},
            pregnant=True,
            use_nlp_extraction=False,
        )

        res = routes_triage.triage(req)
        self.assertEqual(res.triage_level, "RED")
        self.assertTrue(any(m.id == "RF1" for m in res.matched_rules))


if __name__ == "__main__":
    unittest.main()
