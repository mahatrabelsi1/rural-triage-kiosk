from fastapi import APIRouter, Depends, HTTPException, Path, Response

from src.auth import require_staff
from src.pdf.generator import generate_doctor_pdf
from src.storage.db import get_latest_triage_log
from src.triage.schemas import SESSION_ID_PATTERN

router = APIRouter()


def _label(key: str) -> str:
    return key.replace("_", " ")


def build_pdf_fields(request: dict, response: dict) -> dict:
    """Turn a stored triage log into the text fields the PDF prints."""
    chronic = list(request.get("chronic_illnesses") or [])
    other = (request.get("chronic_illnesses_other") or "").strip()
    if other:
        chronic.append(f"other: {other}")

    pregnant = request.get("pregnant")
    return {
        "session_id": response["session_id"],
        "triage_level": response["triage_level"],
        "patient_name": request.get("patient_name", ""),
        "chief_complaint_text": request.get("chief_complaint_text", ""),
        "matched_reasons": [f"{r['id']}: {r['reason']}" for r in response.get("matched_rules", [])],
        "selected_symptoms": [
            f"{_label(s['symptom'])} = {s['rating']}/3" for s in response.get("selected_symptoms", [])
        ],
        "extracted_symptoms": [
            f"{_label(s['symptom'])} = {s['rating']}/3 "
            f"({round(float(s.get('confidence', 0)) * 100)}% confidence, phrase: \"{s.get('source_phrase', 'n/a')}\")"
            for s in response.get("extracted_symptoms", [])
        ],
        "extracted_entities": [
            f"{e['text']} ({e['label']}, {round(float(e.get('score', 0)) * 100)}% confidence)"
            for e in response.get("extracted_entities", [])
        ],
        "advice_blocks": response.get("advice_blocks", []),
        "patient_meta": {
            "entered_by": request.get("entered_by"),
            "age_group": request.get("age_group"),
            "sex": request.get("sex"),
            "pregnant": None if pregnant is None else ("yes" if pregnant else "no"),
            "chronic_illnesses": ", ".join(chronic) if chronic else None,
        },
    }


@router.get("/{session_id}", dependencies=[Depends(require_staff)])
def make_pdf(session_id: str = Path(pattern=SESSION_ID_PATTERN)):
    log = get_latest_triage_log(session_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Session not found")

    pdf_bytes = generate_doctor_pdf(**build_pdf_fields(log["request_payload"], log["response_payload"]))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="triage_{session_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )
