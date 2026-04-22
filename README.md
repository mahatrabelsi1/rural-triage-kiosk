# Rural Triage Kiosk

Rural Triage Kiosk is a clinic intake and prioritization app for low-resource or rural care settings. Staff can record patient details, combine manually selected symptoms with free-text complaint extraction, assign a triage level, and generate a doctor-facing PDF summary.

This project is a triage support tool, not a diagnostic system. It should help staff organize urgency and communicate findings clearly, but it must not replace clinical judgment.

## Highlights

- Captures patient profile details, chief complaint text, and symptom ratings in a kiosk-style UI.
- Uses rule-based triage logic from auditable JSON rules in `rules-and-data/rules.json`.
- Combines manual symptom input with complaint-text extraction.
- Adds a Hugging Face biomedical NER pass for extra symptom/entity detection when enabled.
- Triggers follow-up clarification questions when complaint text is vague or low confidence.
- Forces escalation to `RED` when critical distress language is detected.
- Builds structured advice blocks for staff-facing guidance.
- Stores triage sessions in SQLite for later lookup.
- Generates a printable PDF summary for the clinician.

## Stack

- Frontend: React 18, Vite
- Backend: FastAPI, Pydantic, Uvicorn
- NLP: local extractor plus optional `transformers` / `torch` biomedical NER pipeline
- Storage: SQLite
- PDF: ReportLab
- Tests: Python `unittest`

## How It Works

1. Front desk staff enter patient information and symptom severity ratings.
2. The backend optionally analyzes the chief complaint text to detect symptom mentions and named entities.
3. Manual and extracted symptom scores are merged conservatively.
4. JSON rules determine the triage level: `RED`, `ORANGE`, or `GREEN`.
5. The system returns matched rule reasons, follow-up prompts, extracted entities, and guidance blocks.
6. A PDF handoff summary can be generated for the clinician.

## Triage Levels

- `RED`: urgent clinical review now
- `ORANGE`: prompt same-day review
- `GREEN`: lower immediate risk based on current inputs, with monitoring guidance

## Project Structure

```text
rural-triage-kiosk/
|-- app/
|   |-- backend/
|   |   |-- src/
|   |   |   |-- advice/       # Advice catalog and guidance assembly
|   |   |   |-- api/          # FastAPI routes
|   |   |   |-- nlp/          # Complaint text extraction
|   |   |   |-- pdf/          # PDF generation
|   |   |   |-- storage/      # SQLite persistence
|   |   |   `-- triage/       # Schemas, rules, and engine
|   |   |-- tests/
|   |   |-- .env.example
|   |   `-- requirements.txt
|   `-- frontend/
|       |-- public/assets/
|       |-- src/
|       |   |-- api/
|       |   |-- components/
|       |   `-- pages/
|       `-- package.json
|-- rules-and-data/
|   `-- rules.json
|-- .gitignore
`-- README.md
```

## Local Setup

Run the backend and frontend in separate terminals.

### Backend

```powershell
cd app/backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

Backend URLs:

- App: `http://localhost:8000`
- Health check: `http://localhost:8000/health`

Notes:

- `app/backend/.env.example` is included as a starter, but no required environment variables are defined yet.
- The first use of the Hugging Face biomedical pipeline may download model files locally, depending on your environment and cache state.

### Frontend

```powershell
cd app/frontend
npm install
npm run dev
```

Frontend URL:

- App: `http://localhost:5173`

## API

- `GET /health` checks backend availability.
- `POST /triage` submits intake data and returns triage results, extracted entities, matched rules, and advice blocks.
- `GET /triage/{session_id}` fetches a previously logged session.
- `POST /pdf` generates the doctor-facing summary PDF.

## Testing

From `app/backend`:

```powershell
python -m unittest discover tests
```

Current tests cover:

- Rule-based triage behavior
- Distress-language escalation
- Symptom extraction and merging
- Advice block generation
- Hugging Face extractor normalization
- SQLite logging and retrieval

## Runtime Artifacts

Generated runtime files are written under `app/backend/outputs/`. This directory can contain local databases and PDF exports and should stay out of version control.

## GitHub Remote

The repository is already connected to:

```text
origin https://github.com/mahatrabelsi1/rural-triage-kiosk.git
```

If tracked cache files ever appear again, remove them from the Git index with:

```bash
git rm -r --cached app/backend/src/__pycache__ app/backend/tests/__pycache__
```
