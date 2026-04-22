import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.advice.advice_engine import build_advice_blocks, load_catalog  # noqa: E402


class TestAdviceEngine(unittest.TestCase):
    def setUp(self):
        catalog_path = ROOT / "src" / "advice" / "advice_catalog.json"
        self.catalog = load_catalog(catalog_path)

    def test_green_guidance_uses_symptom_specific_advice(self):
        blocks = build_advice_blocks(
            triage_level="GREEN",
            symptoms={"fever": 1, "cough": 2},
            matched_reasons=[],
            catalog=self.catalog,
        )

        self.assertTrue(any("Lower immediate risk" in block for block in blocks))
        self.assertTrue(any("fluids" in block.lower() for block in blocks))
        self.assertTrue(any("smoke or dust" in block.lower() for block in blocks))

    def test_red_guidance_includes_escalation_language(self):
        blocks = build_advice_blocks(
            triage_level="RED",
            symptoms={"chest_pain": 3},
            matched_reasons=["R1: Severe symptom reported."],
            catalog=self.catalog,
            distress_override=True,
        )

        self.assertTrue(any("immediate clinical review" in block.lower() for block in blocks))
        self.assertTrue(any("critical distress language" in block.lower() for block in blocks))
        self.assertTrue(any("escalate immediately" in block.lower() for block in blocks))


if __name__ == "__main__":
    unittest.main()
