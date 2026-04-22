import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.advice.advice_engine import build_advice_blocks, load_catalog
from src.nlp.extractor import extract_symptom_details_from_text, merge_manual_and_extracted_symptoms
from src.nlp.hf_extractor import process_complaint_text
from src.storage.db import get_latest_triage_log, insert_triage_log
from src.triage.engine import run_triage
from src.triage.rules_loader import load_rules
from src.triage.schemas import (
    ExtractedEntity,
    ExtractedSymptom,
    FollowUpQuestion,
    IntakeRequest,
    MatchedRule,
    SelectedSymptom,
    TriageLogResponse,
    TriageResponse,
)

router = APIRouter()

RULES_PATH = Path(__file__).resolve().parents[4] / "rules-and-data" / "rules.json"
ADVICE_CATALOG_PATH = Path(__file__).resolve().parents[1] / "advice" / "advice_catalog.json"
CRITICAL_DISTRESS_PATTERNS = [
    re.compile(r"\bi\s*(am|m)?\s*(gonna|ganna|gunna|going to)\s*die\b"),
    re.compile(r"\bi\s*am\s*dying\b"),
    re.compile(r"\bi\s*will\s*die\b"),
]

FOLLOW_UP_TEMPLATES = [
    {
        "question_id": "FQ1",
        "symptom": "shortness_of_breath",
        "question_text": "Are you currently short of breath right now?",
        "suggested_rating_if_yes": 3,
        "keywords": ["breath", "breathe", "air", "suffocat"],
    },
    {
        "question_id": "FQ2",
        "symptom": "chest_pain",
        "question_text": "Do you have chest pain or chest tightness now?",
        "suggested_rating_if_yes": 3,
        "keywords": ["chest", "heart", "tight"],
    },
    {
        "question_id": "FQ3",
        "symptom": "confusion",
        "question_text": "Are you confused, disoriented, or unusually drowsy?",
        "suggested_rating_if_yes": 2,
        "keywords": ["confus", "disorient", "drowsy", "faint", "blackout"],
    },
    {
        "question_id": "FQ4",
        "symptom": "bleeding",
        "question_text": "Are you having active bleeding now?",
        "suggested_rating_if_yes": 3,
        "keywords": ["bleed", "blood"],
    },
]


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


def _extracted_entities(items: list[dict]) -> list[ExtractedEntity]:
    return [
        ExtractedEntity(
            text=str(item.get("text", "")),
            label=str(item.get("label", "")),
            score=float(item.get("score", 0.0)),
        )
        for item in items
    ]


def _has_critical_distress_language(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in CRITICAL_DISTRESS_PATTERNS)


def _build_follow_up_questions(
    req: IntakeRequest, extracted_details: list[dict], triage_level: str
) -> list[FollowUpQuestion]:
    if req.clarification_completed:
        return []
    if triage_level == "RED":
        return []
    if not req.use_nlp_extraction:
        return []

    normalized = re.sub(r"\s+", " ", (req.chief_complaint_text or "").lower()).strip()
    if not normalized:
        return []

    selected_manual_count = sum(1 for value in req.symptoms.values() if int(value) >= 1)
    avg_confidence = (
        sum(float(item.get("confidence", 0.0)) for item in extracted_details) / len(extracted_details)
        if extracted_details
        else 0.0
    )
    low_confidence_or_sparse = selected_manual_count == 0 and (
        len(extracted_details) == 0 or avg_confidence < 0.82
    )
    if not low_confidence_or_sparse:
        return []

    questions: list[FollowUpQuestion] = []
    for template in FOLLOW_UP_TEMPLATES:
        keyword_hit = any(keyword in normalized for keyword in template["keywords"])
        if keyword_hit:
            questions.append(FollowUpQuestion(**template))

    if not questions:
        questions = [FollowUpQuestion(**template) for template in FOLLOW_UP_TEMPLATES[:2]]

    return questions[:3]


@router.post("", response_model=TriageResponse)
def triage(req: IntakeRequest):
    session_id = uuid.uuid4().hex[:12]

    rules = load_rules(RULES_PATH)
    allowed_symptoms = rules.get("symptoms", req.symptoms.keys())
    hf_result = process_complaint_text(req.chief_complaint_text) if req.use_nlp_extraction else {
        "entities": [],
        "symptom_scores": {},
    }
    extracted_details = (
        extract_symptom_details_from_text(req.chief_complaint_text, allowed_symptoms)
        if req.use_nlp_extraction
        else []
    )
    hf_symptom_scores = {
        symptom: 1
        for symptom, score in hf_result["symptom_scores"].items()
        if symptom in allowed_symptoms and float(score) >= 0.5
    }
    extracted_map = {item["symptom"]: int(item["rating"]) for item in extracted_details}
    extracted_map.update(
        {symptom: max(int(extracted_map.get(symptom, 0)), rating) for symptom, rating in hf_symptom_scores.items()}
    )
    merged_symptoms = merge_manual_and_extracted_symptoms(req.symptoms, extracted_map)

    triage_level, matched = run_triage(merged_symptoms, rules)
    distress_override = _has_critical_distress_language(req.chief_complaint_text)
    if distress_override:
        triage_level = "RED"
        matched.append(
            MatchedRule(
                id="S1",
                reason="Critical distress language detected in chief complaint.",
            )
        )

    follow_up_questions = _build_follow_up_questions(req, extracted_details, triage_level)
    selected = _selected_symptoms(merged_symptoms)
    extracted = _extracted_symptoms(extracted_details)
    advice_catalog = load_catalog(ADVICE_CATALOG_PATH)
    advice_blocks = build_advice_blocks(
        triage_level=triage_level,
        symptoms=merged_symptoms,
        matched_reasons=[f"{m.id}: {m.reason}" for m in matched],
        catalog=advice_catalog,
        needs_clarification=bool(follow_up_questions),
        distress_override=distress_override,
    )

    response = TriageResponse(
        session_id=session_id,
        triage_level=triage_level,
        selected_symptoms=selected,
        extracted_symptoms=extracted,
        extracted_entities=_extracted_entities(hf_result["entities"]),
        matched_rules=matched,
        advice_blocks=advice_blocks,
        needs_clarification=bool(follow_up_questions),
        follow_up_questions=follow_up_questions,
    )

    insert_triage_log(
        session_id=session_id,
        triage_level=triage_level,
        payload={
            "request": req.model_dump(),
            "response": response.model_dump(),
        },
    )

    return response


@router.get("/{session_id}", response_model=TriageLogResponse)
def get_triage_log(session_id: str):
    log = get_latest_triage_log(session_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return log
