import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.nlp.extractor import (  # noqa: E402
    extract_symptom_details_from_text,
    extract_symptoms_from_text,
    merge_manual_and_extracted_symptoms,
)


class TestNlpExtractor(unittest.TestCase):
    def test_extract_basic_symptoms(self):
        text = "Patient has fever and cough for two days."
        allowed = ["fever", "cough", "headache"]
        extracted = extract_symptoms_from_text(text, allowed)
        self.assertEqual(extracted.get("fever"), 1)
        self.assertEqual(extracted.get("cough"), 1)
        self.assertNotIn("headache", extracted)

    def test_negation_blocks_symptom(self):
        text = "No fever, but has cough and sore throat."
        allowed = ["fever", "cough", "sore_throat"]
        extracted = extract_symptoms_from_text(text, allowed)
        self.assertNotIn("fever", extracted)
        self.assertEqual(extracted.get("cough"), 1)
        self.assertEqual(extracted.get("sore_throat"), 1)

    def test_synonyms_work(self):
        text = "Feels breathless with chest tightness."
        allowed = ["shortness_of_breath", "chest_pain"]
        extracted = extract_symptoms_from_text(text, allowed)
        self.assertEqual(extracted.get("shortness_of_breath"), 1)
        self.assertEqual(extracted.get("chest_pain"), 1)

    def test_merge_keeps_higher_manual_score(self):
        manual = {"fever": 3, "cough": 0}
        extracted = {"fever": 1, "cough": 1}
        merged = merge_manual_and_extracted_symptoms(manual, extracted)
        self.assertEqual(merged["fever"], 3)
        self.assertEqual(merged["cough"], 1)

    def test_extraction_details_include_confidence_and_phrase(self):
        text = "Patient feels breathless and has chest tightness."
        details = extract_symptom_details_from_text(text, ["shortness_of_breath", "chest_pain"])
        self.assertEqual(len(details), 2)
        sob = [d for d in details if d["symptom"] == "shortness_of_breath"][0]
        self.assertEqual(sob["source_phrase"], "breathless")
        self.assertGreaterEqual(float(sob["confidence"]), 0.5)


if __name__ == "__main__":
    unittest.main()
