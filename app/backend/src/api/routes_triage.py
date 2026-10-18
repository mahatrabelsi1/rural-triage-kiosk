import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from src.advice.advice_engine import build_advice_blocks, load_catalog
from src.auth import require_staff
from src.nlp.extractor import extract_symptom_details_from_text, merge_manual_and_extracted_symptoms
from src.nlp.hf_extractor import process_complaint_text
from src.storage.db import get_latest_triage_log, insert_triage_log, list_recent_triage_logs
from src.triage.engine import run_triage
from src.triage.rules_loader import load_rules
from src.triage.safety import detect_critical_language
from src.triage.schemas import (
    ExtractedEntity,
    ExtractedSymptom,
    FollowUpQuestion,
    IntakeRequest,
    MatchedRule,
    SelectedSymptom,
    TriageLogResponse,
    TriageQueueItem,
    TriageResponse,
)

router = APIRouter()

RULES_PATH = Path(__file__).resolve().parents[4] / "rules-and-data" / "rules.json"
ADVICE_CATALOG_PATH = Path(__file__).resolve().parents[1] / "advice" / "advice_catalog.json"
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


def _highest_level(current: str, candidate: str) -> str:
    rank = {"GREEN": 0, "ORANGE": 1, "RED": 2}
    return candidate if rank[candidate] > rank[current] else current


def _has_chronic(req: IntakeRequest, keyword: str) -> bool:
    values = [*req.chronic_illnesses, req.chronic_illnesses_other]
    return any(keyword in (value or "").lower() for value in values)


def _apply_risk_factor_escalation(
    req: IntakeRequest, symptoms: dict[str, int], triage_level: str, matched: list[MatchedRule]
) -> str:
    level = triage_level
    age_group = (req.age_group or "").lower()
    pregnant = bool(req.pregnant)
    has_diabetes = _has_chronic(req, "diabetes")
    has_heart_problem = _has_chronic(req, "heart")

    if pregnant:
        # Any bleeding in pregnancy is treated as an emergency, not only the
        # dedicated "pregnancy_bleeding" symptom.
        if max(int(symptoms.get("pregnancy_bleeding", 0)), int(symptoms.get("bleeding", 0))) >= 1:
            level = _highest_level(level, "RED")
            matched.append(MatchedRule(id="RF1", reason="Pregnancy with bleeding reported."))

        abdominal = int(symptoms.get("abdominal_pain", 0))
        if abdominal >= 2:
            level = _highest_level(level, "RED")
            matched.append(MatchedRule(id="RF8", reason="Pregnancy with moderate or severe abdominal pain."))
        elif abdominal >= 1:
            level = _highest_level(level, "ORANGE")
            matched.append(MatchedRule(id="RF9", reason="Pregnancy with abdominal pain reported."))

    if age_group == "elderly":
        elderly_risk_symptoms = [
            "chest_pain",
            "shortness_of_breath",
            "confusion",
            "fainting",
            "dehydration_signs",
            "severe_weakness",
        ]
        if any(int(symptoms.get(symptom, 0)) >= 2 for symptom in elderly_risk_symptoms):
            level = _highest_level(level, "RED")
            matched.append(MatchedRule(id="RF2", reason="Elderly patient with moderate or severe high-risk symptom."))
        elif any(int(symptoms.get(symptom, 0)) >= 1 for symptom in elderly_risk_symptoms):
            level = _highest_level(level, "ORANGE")
            matched.append(MatchedRule(id="RF3", reason="Elderly patient with high-risk symptom present."))

    if has_diabetes:
        diabetes_risk = max(
            int(symptoms.get("severe_weakness", 0)),
            int(symptoms.get("dehydration_signs", 0)),
            int(symptoms.get("vomiting", 0)),
            int(symptoms.get("diarrhea", 0)),
        )
        if diabetes_risk >= 3:
            level = _highest_level(level, "RED")
            matched.append(MatchedRule(id="RF4", reason="Diabetes with severe weakness, dehydration, vomiting, or diarrhea."))
        elif diabetes_risk >= 2:
            level = _highest_level(level, "ORANGE")
            matched.append(MatchedRule(id="RF5", reason="Diabetes with moderate weakness, dehydration, vomiting, or diarrhea."))

    if has_heart_problem and int(symptoms.get("chest_pain", 0)) >= 1:
        if int(symptoms.get("chest_pain", 0)) >= 2:
            level = _highest_level(level, "RED")
            matched.append(MatchedRule(id="RF6", reason="Heart problem with moderate or worse chest pain."))
        else:
            level = _highest_level(level, "ORANGE")
            matched.append(MatchedRule(id="RF7", reason="Heart problem with chest pain reported."))

    return level


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
    allowed_symptoms = rules.get("symptoms", list(req.symptoms.keys()))
    unknown = sorted(set(req.symptoms) - set(allowed_symptoms))
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown symptom keys: {', '.join(unknown)}")
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
    triage_level = _apply_risk_factor_escalation(req, merged_symptoms, triage_level, matched)
    critical_hits = detect_critical_language(req.chief_complaint_text)
    distress_override = bool(critical_hits)
    if distress_override:
        triage_level = "RED"
        matched.extend(critical_hits)

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
        self_harm_risk=any(hit.id == "S2" for hit in critical_hits),
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


@router.get("", response_model=list[TriageQueueItem], dependencies=[Depends(require_staff)])
def recent_triage_queue(limit: int = 50):
    safe_limit = max(1, min(int(limit), 100))
    return list_recent_triage_logs(safe_limit)


@router.get("/{session_id}", response_model=TriageLogResponse, dependencies=[Depends(require_staff)])
def get_triage_log(session_id: str):
    log = get_latest_triage_log(session_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return log
