from __future__ import annotations

from functools import lru_cache
from typing import Any

try:
    from transformers import pipeline
except Exception:  # pragma: no cover - handled at runtime when dependency is absent
    pipeline = None


HF_MODEL_NAME = "d4data/biomedical-ner-all"

SYMPTOM_MAP = {
    "fever": "fever",
    "pyrexia": "fever",
    "cough": "cough",
    "dyspnea": "shortness_of_breath",
    "shortness of breath": "shortness_of_breath",
    "breathlessness": "shortness_of_breath",
    "headache": "headache",
    "cephalalgia": "headache",
    "chest pain": "chest_pain",
}


@lru_cache(maxsize=1)
def get_ner_pipeline():
    if pipeline is None:
        return None

    return pipeline(
        "token-classification",
        model=HF_MODEL_NAME,
        aggregation_strategy="simple",
    )


def extract_entities(text: str) -> list[dict[str, Any]]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    ner_pipeline = get_ner_pipeline()
    if ner_pipeline is None:
        return []

    results = ner_pipeline(cleaned)
    entities: list[dict[str, Any]] = []
    for item in results:
        entity_text = str(item.get("word", "")).strip()
        if not entity_text:
            continue

        entities.append(
            {
                "text": entity_text,
                "label": str(item.get("entity_group", "")),
                "score": float(item.get("score", 0.0)),
            }
        )

    return entities


def normalize_entities(entities: list[dict[str, Any]]) -> dict[str, float]:
    symptom_scores: dict[str, float] = {}

    for ent in entities:
        raw = str(ent.get("text", "")).lower().strip()
        if raw not in SYMPTOM_MAP:
            continue

        key = SYMPTOM_MAP[raw]
        score = float(ent.get("score", 0.0))
        symptom_scores[key] = max(symptom_scores.get(key, 0.0), score)

    return symptom_scores


def process_complaint_text(text: str) -> dict[str, Any]:
    entities = extract_entities(text)
    symptom_scores = normalize_entities(entities)
    return {
        "entities": entities,
        "symptom_scores": symptom_scores,
    }
