from pathlib import Path
from typing import Dict, List

from src.triage.rules_loader import load_json_cached


def load_catalog(path: Path) -> dict:
    return load_json_cached(path)


def _append_unique(blocks: List[str], text: str) -> None:
    cleaned = text.strip()
    if cleaned and cleaned not in blocks:
        blocks.append(cleaned)


def _symptom_advice(symptoms: Dict[str, int], catalog: dict, limit: int = 4) -> List[str]:
    picked: List[str] = []
    sorted_items = sorted(
        ((key, int(value)) for key, value in symptoms.items() if int(value) >= 1),
        key=lambda item: (-item[1], item[0]),
    )
    for key, _score in sorted_items:
        advice = catalog.get(key)
        if advice:
            _append_unique(picked, advice)
        if len(picked) >= limit:
            break
    return picked


def build_advice_blocks(
    triage_level: str,
    symptoms: Dict[str, int],
    matched_reasons: List[str] | None,
    catalog: dict,
    needs_clarification: bool = False,
    distress_override: bool = False,
    self_harm_risk: bool = False,
) -> List[str]:
    blocks: List[str] = []

    if triage_level == "RED":
        _append_unique(blocks, "Urgent priority: arrange immediate clinical review and avoid delaying care.")
        _append_unique(blocks, "Keep the patient seated or lying safely, minimize walking, and monitor for worsening breathing, bleeding, confusion, or collapse.")
    elif triage_level == "ORANGE":
        _append_unique(blocks, "Prompt review needed: the patient should be seen by a clinician today.")
        _append_unique(blocks, "Keep the patient under observation in the clinic area if symptoms are ongoing or worsening while waiting.")
    else:
        _append_unique(blocks, "Lower immediate risk based on current inputs, but continue monitoring and re-check if symptoms change.")
        _append_unique(blocks, "Encourage rest, oral fluids if tolerated, and avoidance of self-medicating beyond normal clinic guidance.")

    if distress_override:
        _append_unique(blocks, "Critical distress language was detected in the complaint text, so escalation should not wait for more symptom detail.")

    if self_harm_risk:
        _append_unique(blocks, "Possible self-harm risk: do not leave the patient alone, remove objects that could cause harm, and involve a clinician immediately.")

    if matched_reasons:
        joined = "; ".join(matched_reasons[:3])
        _append_unique(blocks, f"Escalation context: {joined}")

    if needs_clarification:
        _append_unique(blocks, "Clarification questions are still recommended because the free-text complaint was vague or low-confidence.")

    for item in _symptom_advice(symptoms, catalog):
        _append_unique(blocks, item)

    if triage_level in {"RED", "ORANGE"}:
        _append_unique(blocks, "If breathing difficulty, chest pain, severe weakness, bleeding, confusion, or fainting worsens, escalate immediately.")
    else:
        _append_unique(blocks, "Seek earlier review if fever rises, pain becomes severe, fluids cannot be kept down, or any new danger signs appear.")

    return blocks
