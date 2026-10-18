"""Regression tests for the safety gaps found in the October 2026 review.

Every case here returned GREEN (or silently dropped a symptom) before the fix.
See TEST_CASES.md at the repo root for the before/after table.
"""

import unittest

from pydantic import ValidationError
from fastapi import HTTPException

from helpers import TempDbMixin
from src.api import routes_triage
from src.nlp.extractor import extract_symptoms_from_text
from src.triage.rules_loader import load_rules
from src.triage.schemas import IntakeRequest

RULES = load_rules(routes_triage.RULES_PATH)
ALL_SYMPTOMS = RULES["symptoms"]


def triage(text="", symptoms=None, **kwargs):
    return routes_triage.triage(
        IntakeRequest(chief_complaint_text=text, symptoms=symptoms or {}, **kwargs)
    )


class TestCriticalLanguage(TempDbMixin, unittest.TestCase):
    def assertRed(self, text, rule_id):
        res = triage(text)
        self.assertEqual(res.triage_level, "RED", text)
        self.assertIn(rule_id, [m.id for m in res.matched_rules], text)
        return res

    def test_distress_with_apostrophes(self):
        for text in [
            "I'm going to die",
            "I’m gonna die",  # curly apostrophe from phone keyboards
            "i think i'm dying",
            "Im about to die",
            "I'll die",
            "help me I am dying",
        ]:
            self.assertRed(text, "S1")

    def test_self_harm_language(self):
        for text in [
            "i want to die",
            "I want to kill myself",
            "thinking about suicide",
            "I don't want to live anymore",
            "i want to end my life",
        ]:
            res = self.assertRed(text, "S2")
            self.assertTrue(any("self-harm" in block.lower() for block in res.advice_blocks))

    def test_distress_is_not_misread_as_self_harm(self):
        res = triage("im gonna die")
        ids = [m.id for m in res.matched_rules]
        self.assertIn("S1", ids)
        self.assertNotIn("S2", ids)

    def test_breathing_emergency_language(self):
        for text in ["I can't breathe", "he is not breathing", "my child is choking", "cannot breathe"]:
            self.assertRed(text, "S3")

    def test_collapse_and_seizure_language(self):
        for text in ["she is unconscious", "having a seizure", "he fainted and is unresponsive"]:
            self.assertRed(text, "S4")

    def test_negated_seizure_history_does_not_force_red(self):
        res = triage("no seizures, mild cough", {"cough": 1})
        self.assertNotIn("S4", [m.id for m in res.matched_rules])


class TestNegationScope(unittest.TestCase):
    def test_negation_stops_at_comma(self):
        extracted = extract_symptoms_from_text("no fever, chest pain since morning", ALL_SYMPTOMS)
        self.assertNotIn("fever", extracted)
        self.assertIn("chest_pain", extracted)

    def test_negation_stops_at_but(self):
        extracted = extract_symptoms_from_text("no fever but headache", ALL_SYMPTOMS)
        self.assertNotIn("fever", extracted)
        self.assertIn("headache", extracted)

    def test_unrelated_negation_does_not_hide_symptom(self):
        extracted = extract_symptoms_from_text("not eating, headache", ALL_SYMPTOMS)
        self.assertIn("headache", extracted)

    def test_negation_still_covers_list_in_same_clause(self):
        extracted = extract_symptoms_from_text("no fever or cough", ALL_SYMPTOMS)
        self.assertNotIn("fever", extracted)
        self.assertNotIn("cough", extracted)

    def test_later_mention_is_found_after_negated_one(self):
        extracted = extract_symptoms_from_text("no headache yesterday, headache today", ALL_SYMPTOMS)
        self.assertIn("headache", extracted)

    def test_contractions_are_negations(self):
        extracted = extract_symptoms_from_text("I don't have a fever", ALL_SYMPTOMS)
        self.assertNotIn("fever", extracted)


class TestSeverityFromText(TempDbMixin, unittest.TestCase):
    def test_severity_words_raise_rating(self):
        extracted = extract_symptoms_from_text("severe chest pain and mild cough", ALL_SYMPTOMS)
        self.assertEqual(extracted["chest_pain"], 3)
        self.assertEqual(extracted["cough"], 1)

    def test_severe_text_alone_escalates(self):
        self.assertEqual(triage("I have severe chest pain").triage_level, "RED")

    def test_cant_breathe_is_extracted(self):
        extracted = extract_symptoms_from_text("I can't breathe properly", ALL_SYMPTOMS)
        self.assertEqual(extracted.get("shortness_of_breath"), 3)


class TestRatingScale(TempDbMixin, unittest.TestCase):
    def test_every_symptom_at_severe_is_never_green(self):
        for symptom in ALL_SYMPTOMS:
            res = triage(symptoms={symptom: 3}, use_nlp_extraction=False)
            self.assertIn(res.triage_level, {"ORANGE", "RED"}, symptom)

    def test_higher_rating_never_lowers_level(self):
        rank = {"GREEN": 0, "ORANGE": 1, "RED": 2}
        for symptom in ALL_SYMPTOMS:
            levels = [
                rank[triage(symptoms={symptom: r}, use_nlp_extraction=False).triage_level]
                for r in range(4)
            ]
            self.assertEqual(levels, sorted(levels), symptom)

    def test_back_pain_severe_is_orange(self):
        self.assertEqual(triage(symptoms={"back_pain": 3}, use_nlp_extraction=False).triage_level, "ORANGE")

    def test_out_of_range_ratings_rejected(self):
        for bad in (-4, 4, 5, 99):
            with self.assertRaises(ValidationError):
                IntakeRequest(symptoms={"chest_pain": bad})

    def test_unknown_symptom_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            triage(symptoms={"made_up": 3})
        self.assertEqual(ctx.exception.status_code, 422)

    def test_invalid_profile_values_rejected(self):
        with self.assertRaises(ValidationError):
            IntakeRequest(symptoms={}, age_group="ancient")
        with self.assertRaises(ValidationError):
            IntakeRequest(symptoms={}, entered_by="robot")


class TestPregnancyEscalation(TempDbMixin, unittest.TestCase):
    def test_pregnant_with_general_bleeding_is_red(self):
        res = triage(symptoms={"bleeding": 1}, pregnant=True, use_nlp_extraction=False)
        self.assertEqual(res.triage_level, "RED")
        self.assertIn("RF1", [m.id for m in res.matched_rules])

    def test_pregnant_with_abdominal_pain(self):
        mild = triage(symptoms={"abdominal_pain": 1}, pregnant=True, use_nlp_extraction=False)
        moderate = triage(symptoms={"abdominal_pain": 2}, pregnant=True, use_nlp_extraction=False)
        self.assertEqual(mild.triage_level, "ORANGE")
        self.assertEqual(moderate.triage_level, "RED")


if __name__ == "__main__":
    unittest.main()
