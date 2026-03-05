from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.pdf.generator import generate_doctor_pdf

router = APIRouter()

OUT_DIR = Path(__file__).resolve().parents[2] / "outputs" / "pdf"


class PdfRequest(BaseModel):
    session_id: str
    triage_level: str
    patient_name: str = ""
    chief_complaint_text: str = ""
    matched_reasons: list[str] = []
    selected_symptoms: list[str] = []
    advice_blocks: list[str] = []
    age_group: str | None = None
    sex: str | None = None
    pregnant: bool | None = None
    chronic_illnesses: list[str] = []
    chronic_illnesses_other: str = ""


@router.post("")
def make_pdf(req: PdfRequest):
    chronic = list(req.chronic_illnesses)
    if req.chronic_illnesses_other.strip():
        chronic.append(f"other: {req.chronic_illnesses_other.strip()}")

    pdf_path = generate_doctor_pdf(
        out_dir=OUT_DIR,
        session_id=req.session_id,
        triage_level=req.triage_level,
        patient_name=req.patient_name,
        chief_complaint_text=req.chief_complaint_text,
        matched_reasons=req.matched_reasons,
        selected_symptoms=req.selected_symptoms,
        advice_blocks=req.advice_blocks,
        patient_meta={
            "age_group": req.age_group,
            "sex": req.sex,
            "pregnant": req.pregnant,
            "chronic_illnesses": ", ".join(chronic) if chronic else None,
        },
    )
    return FileResponse(path=str(pdf_path), filename=pdf_path.name, media_type="application/pdf")
