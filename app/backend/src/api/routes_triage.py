import uuid
from pathlib import Path

from fastapi import APIRouter

from src.nlp.extractor import extract_symptom_details_from_text, merge_manual_and_extracted_symptoms
from src.triage.engine import run_triage
from src.triage.rules_loader import load_rules
from src.triage.schemas import ExtractedSymptom, IntakeRequest, SelectedSymptom, TriageResponse

router = APIRouter()

RULES_PATH = Path(__file__).resolve().parents[4] / "rules-and-data" / "rules.json"


def _selected_symptoms(symptoms: dict[str, int]) -> list[SelectedSymptom]:
    return [
        SelectedSymptom(symptom=key, rating=int(value))
        for key, value in symptoms.items()
        if int(value) >= 1
    ]


def _extracted_symptoms(details: list[dict]) -> list[ExtractedSymptom]:
    return [
        ExtractedSymptom(
            symptom=item["symptom"],
            rating=int(item["rating"]),
            confidence=float(item["confidence"]),
            source_phrase=str(item["source_phrase"]),
        )
        for item in details
    ]


def _advice_from_rules(triage_level: str, matched: list) -> list[str]:
    if matched:
        advice = [f"{m.id}: {m.reason}" for m in matched]
    else:
        advice = []

    if triage_level == "RED":
        advice.append("Immediate clinical review is recommended.")
    elif triage_level == "ORANGE":
        advice.append("Prompt same-day clinical review is recommended.")
    else:
        advice.append("Monitor symptoms and seek care if severity increases.")
        advice.append("Drink water and avoid taking medicine without doctor advice.")
    return advice


@router.post("", response_model=TriageResponse)
def triage(req: IntakeRequest):
    session_id = uuid.uuid4().hex[:12]

    rules = load_rules(RULES_PATH)
    allowed_symptoms = rules.get("symptoms", req.symptoms.keys())
    extracted_details = (
        extract_symptom_details_from_text(req.chief_complaint_text, allowed_symptoms)
        if req.use_nlp_extraction
        else []
    )
    extracted_map = {item["symptom"]: int(item["rating"]) for item in extracted_details}
    merged_symptoms = merge_manual_and_extracted_symptoms(req.symptoms, extracted_map)

    triage_level, matched = run_triage(merged_symptoms, rules)
    selected = _selected_symptoms(merged_symptoms)
    extracted = _extracted_symptoms(extracted_details)
    advice_blocks = _advice_from_rules(triage_level, matched)

    return TriageResponse(
        session_id=session_id,
        triage_level=triage_level,
        selected_symptoms=selected,
        extracted_symptoms=extracted,
        matched_rules=matched,
        advice_blocks=advice_blocks,
    )
