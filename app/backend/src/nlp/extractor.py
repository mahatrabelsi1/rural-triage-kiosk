import re
from typing import Dict, Iterable

NEGATION_TERMS = {
    "no",
    "not",
    "without",
    "denies",
    "deny",
    "denied",
    "none",
    "never",
}

SYMPTOM_SYNONYMS: dict[str, list[str]] = {
    "fever": ["fever", "high temperature", "hot body"],
    "cough": ["cough", "coughing"],
    "shortness_of_breath": ["shortness of breath", "breathless", "difficulty breathing"],
    "chest_pain": ["chest pain", "chest tightness", "tight chest"],
    "sore_throat": ["sore throat", "throat pain"],
    "chills": ["chills", "shivering"],
    "fatigue": ["fatigue", "tired", "weak", "exhausted"],
    "body_aches": ["body aches", "body pain", "muscle aches"],
    "rash": ["rash", "skin rash"],
    "abdominal_pain": ["abdominal pain", "stomach pain", "belly pain"],
    "nausea": ["nausea", "nauseous", "queasy"],
    "vomiting": ["vomiting", "throwing up", "vomit"],
    "diarrhea": ["diarrhea", "loose stool", "watery stool"],
    "dehydration_signs": ["dehydrated", "dry mouth", "sunken eyes"],
    "headache": ["headache", "head pain"],
    "dizziness": ["dizziness", "dizzy", "lightheaded"],
    "fainting": ["fainting", "passed out", "blackout"],
    "confusion": ["confusion", "confused", "disoriented"],
    "severe_weakness": ["severe weakness", "very weak", "cannot stand"],
    "bleeding": ["bleeding", "blood loss", "bleed"],
    "head_injury": ["head injury", "hit head", "head trauma"],
    "back_pain": ["back pain", "lower back pain"],
    "urination_pain": ["painful urination", "burning urination", "urine pain"],
    "allergic_reaction": ["allergic reaction", "allergy attack", "swelling after food"],
    "pregnancy_bleeding": ["pregnancy bleeding", "bleeding in pregnancy"],
}


def _normalize(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", lowered)).strip()


def _is_negated(normalized: str, phrase_start: int) -> bool:
    left_context = normalized[max(0, phrase_start - 40):phrase_start].split()
    return any(token in NEGATION_TERMS for token in left_context[-3:])


def _confidence_for_phrase(symptom: str, phrase: str) -> float:
    canonical = symptom.replace("_", " ")
    if phrase == canonical:
        return 0.92
    if phrase.split()[0] in canonical:
        return 0.85
    return 0.78


def extract_symptom_details_from_text(
    text: str, allowed_symptoms: Iterable[str]
) -> list[dict]:
    normalized = _normalize(text)
    if not normalized:
        return []

    allowed = set(allowed_symptoms)
    details: list[dict] = []

    for symptom, phrases in SYMPTOM_SYNONYMS.items():
        if symptom not in allowed:
            continue

        for phrase in phrases:
            pattern = re.compile(rf"\b{re.escape(phrase)}\b")
            match = pattern.search(normalized)
            if not match:
                continue

            if _is_negated(normalized, match.start()):
                continue

            details.append(
                {
                    "symptom": symptom,
                    "rating": 1,
                    "confidence": _confidence_for_phrase(symptom, phrase),
                    "source_phrase": phrase,
                }
            )
            break

    details.sort(key=lambda x: x["symptom"])
    return details


def extract_symptoms_from_text(
    text: str, allowed_symptoms: Iterable[str]
) -> Dict[str, int]:
    extracted: Dict[str, int] = {}
    for item in extract_symptom_details_from_text(text, allowed_symptoms):
        extracted[item["symptom"]] = max(extracted.get(item["symptom"], 0), int(item["rating"]))
    return extracted


def merge_manual_and_extracted_symptoms(
    manual: Dict[str, int], extracted: Dict[str, int]
) -> Dict[str, int]:
    merged = {k: int(v) for k, v in manual.items()}
    for symptom, score in extracted.items():
        merged[symptom] = max(int(merged.get(symptom, 0)), int(score))
    return merged
