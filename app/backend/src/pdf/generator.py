from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _draw_line(c: canvas.Canvas, text: str, y: int, x: int = 60) -> int:
    c.drawString(x, y, text[:130])
    return y - 12


def generate_doctor_pdf(
    out_dir: Path,
    session_id: str,
    triage_level: str,
    patient_name: str,
    chief_complaint_text: str,
    matched_reasons: list[str],
    selected_symptoms: list[str],
    advice_blocks: list[str],
    patient_meta: dict,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"triage_{session_id}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    _, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Rural Clinic Triage Summary (Non-diagnostic)")

    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Session ID: {session_id}")
    y -= 15
    c.drawString(50, y, f"Triage Level: {triage_level}")

    y -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Patient Snapshot")
    y -= 15
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Name: {patient_name or 'N/A'}")
    y -= 12
    meta_line = " | ".join([f"{k}: {v}" for k, v in patient_meta.items() if v is not None and v != ""])
    c.drawString(50, y, meta_line if meta_line else "N/A")

    y -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Chief Complaint (verbatim)")
    y -= 15
    c.setFont("Helvetica", 10)
    complaint = chief_complaint_text.strip() or "N/A"
    c.drawString(50, y, complaint[:130] + ("..." if len(complaint) > 130 else ""))

    y -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Selected Symptoms (1-5)")
    y -= 15
    c.setFont("Helvetica", 10)
    if selected_symptoms:
        for item in selected_symptoms[:15]:
            y = _draw_line(c, f"- {item}", y)
    else:
        y = _draw_line(c, "- None selected", y)

    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Matched Rule Reasons")
    y -= 15
    c.setFont("Helvetica", 10)
    if matched_reasons:
        for reason in matched_reasons[:10]:
            y = _draw_line(c, f"- {reason}", y)
    else:
        y = _draw_line(c, "- None (GREEN default)", y)

    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Guidance / Advice")
    y -= 15
    c.setFont("Helvetica", 10)
    for block in advice_blocks[:10]:
        y = _draw_line(c, f"- {block}", y)

    y -= 20
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "Safety note: This tool does not provide a medical diagnosis. It supports prioritization only.")

    c.showPage()
    c.save()
    return pdf_path
