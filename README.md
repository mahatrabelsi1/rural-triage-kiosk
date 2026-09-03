# Rural Triage Kiosk

A full triage-support product for low-resource and rural care settings. Staff record patient details, combine manually rated symptoms with free-text NLP extraction, and receive a prioritized triage level with clinician-facing guidance. An optional voice accessibility layer narrates prompts through a virtual nurse avatar. A dedicated safety-test suite verifies correct escalation across critical scenarios.

This is a triage support tool, not a diagnostic system. It helps staff organize urgency and communicate findings clearly, but must not replace clinical judgment.

---

## Demonstrated Safety Performance

All 20 tests pass (run `python -m unittest discover tests` from `app/backend`).

### Safety escalation (test_triage_safety.py — 8/8 pass)

| Scenario | Expected | Result |
|---|---|---|
| Distress language: "im gonna die" | RED | PASS |
| Distress language with typo: "im ganna die" | RED | PASS |
| Diabetes + severe dehydration (rating 3) | RED | PASS |
| Pregnancy + bleeding | RED | PASS |
| Elderly patient + high-risk symptom (rating 1) | ORANGE | PASS |
| Cardiac history + chest pain (rating 1) | ORANGE | PASS |
| Vague complaint, no manual symptoms → clarification triggered | follow-up questions | PASS |
| Clarification completed flag → follow-up suppressed | no follow-up | PASS |

**RED escalation sensitivity: 4/4 tested scenarios correctly escalated (100%).**
Distress detection includes typo-tolerant pattern matching (e.g. "ganna" → "gonna").

### Supporting tests

| Suite | Tests | All pass |
|---|---|---|
| `test_triage_logging.py` | 3 — session logging, 404 handling, urgency-sorted queue | Yes |
| `test_advice_engine.py` | 2 — GREEN guidance, RED escalation language | Yes |
| `test_nlp_extractor.py` | 5 — basic extraction, negation blocking, synonym mapping, merge logic, confidence details | Yes |
| `test_hf_extractor.py` | 2 — entity normalization, HF pipeline output mapping | Yes |

---

## What the System Does

1. Front desk staff enter patient profile information and rate symptom severity (0–3 scale).
2. The backend optionally analyzes the chief complaint text to detect symptom mentions and named medical entities.
3. Manual and NLP-extracted symptom scores are merged conservatively (highest score wins).
4. A Hugging Face biomedical NER pass (when enabled) adds an extra entity detection layer.
5. JSON rules in `rules-and-data/rules.json` determine the base triage level: `RED`, `ORANGE`, or `GREEN`.
6. Patient risk factors (elderly, pregnancy, diabetes, cardiac history) can independently escalate urgency.
7. Critical distress language in the complaint text unconditionally forces `RED`.
8. When the complaint is vague or low-confidence with no manual symptoms selected, targeted follow-up questions are surfaced.
9. The system returns matched rule reasons, follow-up prompts, extracted entities, and structured guidance blocks for staff.
10. Clinicians review a priority-sorted queue (`RED` → `ORANGE` → `GREEN`) and can open per-session summaries.
11. A printable PDF handoff summary is generated for the consulting clinician.
12. An optional virtual nurse avatar narrates prompts aloud via a Hugging Face TTS model, with browser speech synthesis as a fallback.

---

## Highlights

- Captures patient profile, chief complaint text, and per-symptom severity ratings in a kiosk-style React UI.
- Rule-based triage logic from auditable JSON (`rules-and-data/rules.json`) — every escalation is traceable to a named rule.
- Hybrid NLP: local keyword/synonym extractor plus optional `transformers` biomedical NER pipeline.
- Distress-language safety override: unconditional RED for phrases such as "I'm going to die" including common typo variants.
- Risk-factor escalation layer: elderly, pregnant, diabetic, and cardiac patients receive appropriate urgency boosts.
- Clarification prompts when complaint text is vague or NLP confidence is low.
- Structured advice blocks assembled per triage level and matched symptoms.
- SQLite session store with a clinician queue sorted by urgency.
- PDF summary generation via ReportLab.
- Optional voice accessibility layer using Hugging Face `Vedika35/Vedika_text_to_speech` with browser fallback.

---

## Triage Levels

| Level | Meaning |
|---|---|
| `RED` | Urgent clinical review now |
| `ORANGE` | Prompt same-day review |
| `GREEN` | Lower immediate risk; monitor with guidance |

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite |
| Backend | FastAPI, Pydantic, Uvicorn |
| NLP | Local keyword/synonym extractor + optional `transformers` / `torch` biomedical NER |
| Storage | SQLite |
| PDF | ReportLab |
| Voice | Hugging Face TTS pipeline (`Vedika35/Vedika_text_to_speech`) with browser speech fallback |
| Tests | Python `unittest` |

---

## Project Structure

```text
rural-triage-kiosk/
├── app/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── advice/       # Advice catalog (JSON) and guidance assembly engine
│   │   │   ├── api/          # FastAPI routes: triage, PDF, speech
│   │   │   ├── nlp/          # Local symptom extractor and HF biomedical NER wrapper
│   │   │   ├── pdf/          # PDF report generation
│   │   │   ├── storage/      # SQLite session persistence
│   │   │   └── triage/       # Schemas, rules loader, and triage engine
│   │   ├── tests/
│   │   │   ├── test_triage_safety.py    # Safety-critical escalation scenarios
│   │   │   ├── test_triage_logging.py   # Session logging and queue ordering
│   │   │   ├── test_advice_engine.py    # Advice block assembly
│   │   │   ├── test_nlp_extractor.py    # Local NLP extraction
│   │   │   └── test_hf_extractor.py     # HF entity normalization
│   │   ├── .env.example
│   │   └── requirements.txt
│   └── frontend/
│       ├── public/assets/       # Static assets including avatar video
│       ├── src/
│       │   ├── api/             # Axios client
│       │   ├── components/      # AvatarAssistant (voice + video)
│       │   └── pages/           # Welcome, Intake, Result, Queue
│       ├── index.html
│       └── package.json
├── rules-and-data/
│   └── rules.json               # Auditable triage rules (RED/ORANGE conditions)
├── .gitignore
└── README.md
```

---

## Local Setup

Run backend and frontend in separate terminals. All commands below assume you start from the **repo root** (`rural-triage-kiosk/`).

> **If your `.venv` was created at a different path** (e.g. after moving the repo folder), delete it and recreate it — Python venvs store absolute paths internally and break when moved:
> ```powershell
> Remove-Item -Recurse -Force app\backend\.venv
> ```
> Then follow the setup steps below.

### Backend

```powershell
# From repo root:
cd app\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

| URL | Purpose |
|---|---|
| `http://localhost:8000` | Backend root |
| `http://localhost:8000/health` | Health check |

**Notes:**
- Copy `.env.example` to `.env` before starting. `TTS_MODEL_NAME` defaults to `Vedika35/Vedika_text_to_speech`.
- First use of the Hugging Face biomedical pipeline may download model files locally.
- First avatar speech request may download the configured TTS model. Browsers may require one user gesture before audio playback is allowed.

### Frontend

```powershell
# From repo root:
cd app\frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

---

## API Reference

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Backend health check |
| `POST` | `/triage` | Submit intake data; returns triage level, matched rules, extracted entities, advice blocks |
| `GET` | `/triage?limit=50` | List recent sessions sorted by urgency (RED first) |
| `GET` | `/triage/{session_id}` | Fetch a previously logged session |
| `POST` | `/pdf` | Generate the doctor-facing PDF summary |
| `POST` | `/speech` | Generate avatar narration audio from text |

---

## Running Tests

From `app/backend`:

```powershell
python -m unittest discover tests
```

Or verbose:

```powershell
python -m unittest discover tests -v
```

---

## Runtime Artifacts

Generated files are written under `app/backend/outputs/` (SQLite databases, PDF exports). This directory is excluded from version control.

---

## GitHub Remote

```text
origin https://github.com/mahatrabelsi1/rural-triage-kiosk.git
```

If tracked cache files ever appear again, remove them from the Git index with:

```bash
git rm -r --cached app/backend/src/__pycache__ app/backend/tests/__pycache__
```
