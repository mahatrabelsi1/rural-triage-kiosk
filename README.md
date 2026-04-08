# Rural Triage Kiosk

Rural Triage Kiosk is a local clinic intake tool that helps staff capture patient details, rate symptoms, assign a triage priority, and generate a doctor-facing PDF summary. It is designed as a prioritization support system for rural or low-resource clinic workflows, not as a diagnostic tool.

## What It Does

- Collects patient name, age group, sex, pregnancy status, chronic illness information, and chief complaint text.
- Lets staff rate symptoms from 0 to 5 across respiratory, digestive, neurologic, and urgent categories.
- Uses a simple local keyword-based NLP extractor to detect symptoms from the chief complaint text.
- Merges manually entered symptoms with extracted symptoms while keeping the higher severity score.
- Applies auditable JSON triage rules to classify cases as `RED`, `ORANGE`, or `GREEN`.
- Triggers safety clarification questions when the complaint is vague or low-confidence.
- Forces `RED` priority for critical distress language such as "I am dying" or common typo variants.
- Logs triage sessions in SQLite for later lookup.
- Generates a doctor summary PDF with patient snapshot, complaint, selected symptoms, matched rule reasons, and guidance.
- Shows a kiosk-style React interface with a virtual nurse assistant video panel.

## Tech Stack

- Frontend: React 18, Vite, CSS
- Backend: FastAPI, Pydantic, Uvicorn
- Rules: JSON rules in `rules-and-data/rules.json`
- Storage: SQLite
- PDF generation: ReportLab
- Tests: Python `unittest`

## Project Structure

```text
rural-triage-kiosk/
|-- app/
|   |-- backend/
|   |   |-- src/
|   |   |   |-- api/          # FastAPI routes for triage and PDF generation
|   |   |   |-- advice/       # Advice catalog and advice engine
|   |   |   |-- nlp/          # Local symptom text extraction
|   |   |   |-- pdf/          # Doctor PDF generator
|   |   |   |-- storage/      # SQLite logging
|   |   |   `-- triage/       # Schemas, rule loading, and triage engine
|   |   |-- tests/            # Backend safety, logging, and NLP tests
|   |   `-- requirements.txt
|   `-- frontend/
|       |-- public/assets/    # Virtual nurse video asset
|       |-- src/
|       |   |-- api/          # Frontend API client
|       |   |-- components/   # Virtual nurse assistant component
|       |   `-- pages/        # Welcome, intake, and result screens
|       `-- package.json
|-- rules-and-data/
|   `-- rules.json            # Auditable triage rules
`-- README.md
```

## Triage Levels

- `RED`: urgent clinical review. Triggered by severe symptoms, high-risk symptoms, dangerous combinations, or critical distress language.
- `ORANGE`: prompt same-day clinical review. Triggered by moderate symptoms or concerning combinations.
- `GREEN`: monitor symptoms and seek care if severity increases.

Safety note: this tool supports triage prioritization only. It does not diagnose patients, replace a clinician, or make treatment decisions.

## Run Locally

Open two terminals: one for the backend and one for the frontend.

### Backend

```bash
cd app/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

The backend runs at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

### Frontend

```bash
cd app/frontend
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:5173
```

## API Endpoints

- `GET /health`: checks that the FastAPI server is running.
- `POST /triage`: submits patient intake data and returns the triage result.
- `GET /triage/{session_id}`: retrieves a logged triage session.
- `POST /pdf`: generates and downloads a doctor summary PDF.

## Run Tests

From the backend folder:

```bash
cd app/backend
python -m unittest discover tests
```

The tests cover:

- Symptom extraction and negation handling.
- Manual and extracted symptom merging.
- Critical distress language safety override.
- Follow-up clarification logic.
- SQLite logging and session retrieval.

## Runtime Outputs

The backend writes runtime files under:

```text
app/backend/outputs/
```

That folder may contain local SQLite databases and generated PDFs. These are runtime artifacts and should not be committed to GitHub.

## Push To GitHub

This project already has a remote configured:

```text
origin https://github.com/mahatrabelsi1/rural-triage-kiosk.git
```

Use these commands from the project root:

```bash
git status
git add README.md .gitignore
git add app/backend/src/main.py app/backend/src/api/routes_pdf.py app/backend/src/api/routes_triage.py
git add app/backend/src/nlp/extractor.py app/backend/src/pdf/generator.py app/backend/src/storage/db.py
git add app/backend/src/triage/engine.py app/backend/src/triage/rules_loader.py app/backend/src/triage/schemas.py
git add app/backend/tests app/frontend/src app/frontend/public app/frontend/package.json app/frontend/package-lock.json app/frontend/index.html app/frontend/vite.config.js rules-and-data
git status
git commit -m "Improve rural triage kiosk documentation"
git push origin main
```

If Git still shows tracked `__pycache__` files, remove them from Git tracking before committing:

```bash
git rm -r --cached app/backend/src/__pycache__ app/backend/src/api/__pycache__ app/backend/src/pdf/__pycache__ app/backend/src/triage/__pycache__
git status
```

If this is your first push and Git asks you to log in, use your GitHub username and a GitHub personal access token instead of your account password.
