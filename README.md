# Rural Triage Kiosk

Offline starter architecture for a rural clinic triage kiosk:

- React (Vite) frontend kiosk UI
- FastAPI backend
- JSON rules (auditable)
- SQLite logging (starter file included)
- PDF doctor summary (ReportLab)

## Structure

See `app/` and `rules-and-data/` for backend, frontend, and rules files.

## Run

Backend (`app/backend`):

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

Frontend (`app/frontend`):

```bash
npm install
npm run dev
```
