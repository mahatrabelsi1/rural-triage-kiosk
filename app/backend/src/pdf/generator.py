from pathlib import Path
import textwrap

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

LEVEL_THEME = {
    "GREEN": {
        "banner": colors.HexColor("#1E8D68"),
        "title": colors.HexColor("#0F5A42"),
        "soft": colors.HexColor("#EAF8F2"),
    },
    "ORANGE": {
        "banner": colors.HexColor("#DA861F"),
        "title": colors.HexColor("#8F4F08"),
        "soft": colors.HexColor("#FFF4E8"),
    },
    "RED": {
        "banner": colors.HexColor("#C64848"),
        "title": colors.HexColor("#7F2222"),
        "soft": colors.HexColor("#FDEEEE"),
    },
}


def _level_theme(triage_level: str) -> dict:
    return LEVEL_THEME.get(triage_level, LEVEL_THEME["GREEN"])


def _draw_wrapped_text(c: canvas.Canvas, text: str, y: int, x: int = 56, width: int = 98, line_gap: int = 13) -> int:
    for line in textwrap.wrap(text, width=width) or [""]:
        c.drawString(x, y, line)
        y -= line_gap
    return y


def _draw_bullet_list(c: canvas.Canvas, items: list[str], y: int, width: int = 96, max_items: int = 14) -> int:
    for item in items[:max_items]:
        wrapped = textwrap.wrap(item, width=width)
        if not wrapped:
            continue
        c.drawString(60, y, f"- {wrapped[0]}")
        y -= 12
        for continuation in wrapped[1:]:
            c.drawString(72, y, continuation)
            y -= 12
    return y


def _draw_section_title(c: canvas.Canvas, title: str, y: int) -> int:
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#13313D"))
    c.drawString(50, y, title)
    c.setLineWidth(0.8)
    c.setStrokeColor(colors.HexColor("#D3E6EA"))
    c.line(50, y - 4, 545, y - 4)
    return y - 18


def _draw_footer(c: canvas.Canvas, page_width: float) -> None:
    c.setStrokeColor(colors.HexColor("#D3E6EA"))
    c.line(50, 64, page_width - 50, 64)
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.HexColor("#55727E"))
    c.drawString(
        50,
        50,
        "Safety note: This tool does not provide diagnosis. It supports triage prioritization only.",
    )


def _ensure_space(c: canvas.Canvas, y: int, needed: int, page_width: float, page_height: float) -> int:
    if y >= needed:
        return y

    _draw_footer(c, page_width)
    c.showPage()
    return page_height - 60


def generate_doctor_pdf(
    out_dir: Path,
    session_id: str,
    triage_level: str,
    patient_name: str,
    chief_complaint_text: str,
    matched_reasons: list[str],
    selected_symptoms: list[str],
    extracted_symptoms: list[str],
    extracted_entities: list[str],
    advice_blocks: list[str],
    patient_meta: dict,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"triage_{session_id}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    page_width, page_height = A4
    theme = _level_theme(triage_level)

    # Header block
    c.setFillColor(theme["banner"])
    c.roundRect(40, page_height - 124, page_width - 80, 78, 12, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(56, page_height - 74, "Rural Clinic Triage Summary")

    c.setFont("Helvetica", 10)
    c.drawString(56, page_height - 92, "Clinical prioritization support document (non-diagnostic)")
    c.drawRightString(page_width - 56, page_height - 74, f"Level: {triage_level}")
    c.drawRightString(page_width - 56, page_height - 92, f"Session: {session_id}")

    # Level badge
    c.setFillColor(theme["soft"])
    c.roundRect(50, page_height - 162, 170, 25, 10, stroke=0, fill=1)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(theme["title"])
    c.drawString(60, page_height - 146, f"Priority: {triage_level}")

    y = page_height - 184

    # Patient Snapshot
    y = _ensure_space(c, y, 130, page_width, page_height)
    y = _draw_section_title(c, "Patient Snapshot", y)
    c.setFillColor(colors.HexColor("#13313D"))
    c.setFont("Helvetica", 10)
    y = _draw_wrapped_text(c, f"Name: {patient_name or 'N/A'}", y)
    meta_line = " | ".join(
        [f"{k}: {v}" for k, v in patient_meta.items() if v is not None and v != ""]
    )
    y = _draw_wrapped_text(c, meta_line if meta_line else "N/A", y)

    # Chief complaint
    y -= 8
    y = _ensure_space(c, y, 140, page_width, page_height)
    y = _draw_section_title(c, "Chief Complaint (verbatim)", y)
    complaint = chief_complaint_text.strip() or "N/A"
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#1B3A48"))
    y = _draw_wrapped_text(c, complaint, y, width=98)

    # Selected symptoms
    y -= 8
    y = _ensure_space(c, y, 170, page_width, page_height)
    y = _draw_section_title(c, "Selected Symptoms (1-5)", y)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#13313D"))
    if selected_symptoms:
        y = _draw_bullet_list(c, selected_symptoms, y, max_items=16)
    else:
        y = _draw_bullet_list(c, ["None selected"], y, max_items=1)

    # NLP summary
    y -= 8
    y = _ensure_space(c, y, 190, page_width, page_height)
    y = _draw_section_title(c, "NLP Summary", y)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#13313D"))
    if extracted_symptoms:
        y = _draw_bullet_list(c, extracted_symptoms, y, max_items=12)
    else:
        y = _draw_bullet_list(c, ["No normalized symptoms extracted from free text."], y, max_items=1)

    y -= 6
    y = _ensure_space(c, y, 145, page_width, page_height)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#13313D"))
    c.drawString(50, y, "Detected biomedical entities")
    y -= 16
    c.setFont("Helvetica", 10)
    if extracted_entities:
        y = _draw_bullet_list(c, extracted_entities, y, max_items=12)
    else:
        y = _draw_bullet_list(c, ["No biomedical entities extracted."], y, max_items=1)

    # Matched reasons
    y -= 8
    y = _ensure_space(c, y, 170, page_width, page_height)
    y = _draw_section_title(c, "Matched Rule Reasons", y)
    c.setFont("Helvetica", 10)
    if matched_reasons:
        y = _draw_bullet_list(c, matched_reasons, y, max_items=12)
    else:
        y = _draw_bullet_list(c, ["None (GREEN default)"], y, max_items=1)

    # Guidance
    y -= 8
    y = _ensure_space(c, y, 170, page_width, page_height)
    y = _draw_section_title(c, "Guidance / Advice", y)
    c.setFont("Helvetica", 10)
    y = _draw_bullet_list(c, advice_blocks, y, max_items=12)

    _draw_footer(c, page_width)
    c.showPage()
    c.save()
    return pdf_path
