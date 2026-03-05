from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes_triage import router as triage_router
from src.api.routes_pdf import router as pdf_router

app = FastAPI(title="Rural Triage Kiosk", version="0.1.0")

# Offline kiosk: frontend runs on localhost too, allow it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(triage_router, prefix="/triage", tags=["triage"])
app.include_router(pdf_router, prefix="/pdf", tags=["pdf"])

@app.get("/health")
def health():
    return {"status": "ok"}

