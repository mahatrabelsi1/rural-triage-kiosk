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
    "dont",
    "doesnt",
    "didnt",
    "havent",
    "hasnt",
}

# Negation never carries across these boundaries: "no fever, chest pain" or
# "no fever but chest pain" must still detect chest pain.
CLAUSE_BREAK_WORDS = {"but", "however", "although", "though", "except", "yet"}

# Severity words found just before a symptom phrase raise the extracted rating
# (0-3 scale). Extraction only ever escalates; it never lowers a manual rating.
SEVERITY_MODIFIERS: dict[str, int] = {
    "mild": 1,
    "slight": 1,
    "little": 1,
    "moderate": 2,
    "bad": 2,
    "strong": 2,
    "severe": 3,
    "terrible": 3,
    "unbearable": 3,
    "extreme": 3,
    "worst": 3,
    "intense": 3,
    "crushing": 3,
    "heavy": 3,
}

SYMPTOM_SYNONYMS: dict[str, list[str]] = {
    "fever": ["fever", "high temperature", "hot body", "feverish"],
    "cough": ["cough", "coughing"],
    "shortness_of_breath": [
        "shortness of breath",
        "short of breath",
        "breathless",
        "difficulty breathing",
        "trouble breathing",
        "hard to breathe",
        "struggling to breathe",
        "cant breathe",
        "cannot breathe",
    ],
    "chest_pain": ["chest pain", "chest tightness", "tight chest", "chest hurts", "pain in my chest", "pain in chest"],
    "sore_throat": ["sore throat", "throat pain"],
    "chills": ["chills", "shivering"],
    "fatigue": ["fatigue", "tired", "weak", "exhausted"],
    "body_aches": ["body aches", "body pain", "muscle aches"],
    "rash": ["rash", "skin rash"],
    "abdominal_pain": ["abdominal pain", "stomach pain", "belly pain", "stomach ache", "tummy pain"],
    "nausea": ["nausea", "nauseous", "queasy"],
    "vomiting": ["vomiting", "throwing up", "vomit"],
    "diarrhea": ["diarrhea", "diarrhoea", "loose stool", "watery stool"],
    "dehydration_signs": ["dehydrated", "dry mouth", "sunken eyes"],
    "headache": ["headache", "head pain", "head hurts"],
    "dizziness": ["dizziness", "dizzy", "lightheaded"],
    "fainting": ["fainting", "fainted", "passed out", "blackout"],
    "confusion": ["confusion", "confused", "disoriented"],
    "severe_weakness": ["severe weakness", "very weak", "cannot stand", "cant stand"],
    "bleeding": ["bleeding", "blood loss", "bleed"],
    "head_injury": ["head injury", "hit head", "hit my head", "head trauma"],
    "back_pain": ["back pain", "lower back pain"],
    "urination_pain": ["painful urination", "burning urination", "urine pain"],
    "allergic_reaction": ["allergic reaction", "allergy attack", "swelling after food"],
    "pregnancy_bleeding": ["pregnancy bleeding", "bleeding in pregnancy"],
}

# Some phrases already state their severity, so they don't need a modifier.
INHERENT_SEVERITY: dict[str, int] = {
    "severe weakness": 3,
    "very weak": 3,
    "cannot stand": 3,
    "cant stand": 3,
    "cant breathe": 3,
    "cannot breathe": 3,
    "struggling to breathe": 3,
}

_CLAUSE_PUNCTUATION = re.compile(r"[.,;:!?\n]+")


def _normalize(text: str) -> str:
    lowered = re.sub(r"['’‘`´]", "", text.lower())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", lowered)).strip()


def _clauses(text: str) -> list[str]:
    """Split text into clauses so negation and severity stay local."""
    clauses: list[str] = []
    for chunk in _CLAUSE_PUNCTUATION.split(text or ""):
        current: list[str] = []
        for token in _normalize(chunk).split():
            if token in CLAUSE_BREAK_WORDS:
                if current:
                    clauses.append(" ".join(current))
                current = []
                continue
            current.append(token)
        if current:
            clauses.append(" ".join(current))
    return clauses


def _left_tokens(clause: str, phrase_start: int, count: int = 3) -> list[str]:
    return clause[:phrase_start].split()[-count:]


def _is_negated(clause: str, phrase_start: int) -> bool:
    return any(token in NEGATION_TERMS for token in _left_tokens(clause, phrase_start))


def _severity_for(clause: str, phrase_start: int, phrase: str) -> int:
    rating = INHERENT_SEVERITY.get(phrase, 1)
    for token in _left_tokens(clause, phrase_start):
        rating = max(rating, SEVERITY_MODIFIERS.get(token, 0))
    return rating


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
    clauses = _clauses(text)
    if not clauses:
        return []

    allowed = set(allowed_symptoms)
    best: dict[str, dict] = {}

    for symptom, phrases in SYMPTOM_SYNONYMS.items():
        if symptom not in allowed:
            continue

        for phrase in phrases:
            pattern = re.compile(rf"\b{re.escape(phrase)}\b")
            for clause in clauses:
                for match in pattern.finditer(clause):
                    if _is_negated(clause, match.start()):
                        continue

                    candidate = {
                        "symptom": symptom,
                        "rating": _severity_for(clause, match.start(), phrase),
                        "confidence": _confidence_for_phrase(symptom, phrase),
                        "source_phrase": phrase,
                    }
                    current = best.get(symptom)
                    if current is None or (candidate["rating"], candidate["confidence"]) > (
                        current["rating"],
                        current["confidence"],
                    ):
                        best[symptom] = candidate

    return sorted(best.values(), key=lambda x: x["symptom"])


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
