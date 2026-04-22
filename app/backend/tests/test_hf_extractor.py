import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.nlp.hf_extractor import normalize_entities, process_complaint_text  # noqa: E402


class TestHfExtractor(unittest.TestCase):
    def test_normalize_entities_maps_known_terms(self):
        entities = [
            {"text": "pyrexia", "label": "SIGN_SYMPTOM", "score": 0.91},
            {"text": "chest pain", "label": "SIGN_SYMPTOM", "score": 0.88},
            {"text": "unknown", "label": "SIGN_SYMPTOM", "score": 0.99},
        ]

        normalized = normalize_entities(entities)

        self.assertEqual(normalized["fever"], 0.91)
        self.assertEqual(normalized["chest_pain"], 0.88)
        self.assertNotIn("unknown", normalized)

    @patch("src.nlp.hf_extractor.extract_entities")
    def test_process_complaint_text_returns_entities_and_scores(self, mock_extract_entities):
        mock_extract_entities.return_value = [
            {"text": "fever", "label": "SIGN_SYMPTOM", "score": 0.98},
            {"text": "dyspnea", "label": "SIGN_SYMPTOM", "score": 0.87},
        ]

        result = process_complaint_text("fever and dyspnea")

        self.assertEqual(len(result["entities"]), 2)
        self.assertEqual(result["symptom_scores"]["fever"], 0.98)
        self.assertEqual(result["symptom_scores"]["shortness_of_breath"], 0.87)


if __name__ == "__main__":
    unittest.main()
