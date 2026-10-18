from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.api.routes_auth import router as auth_router
from src.api.routes_pdf import router as pdf_router
from src.api.routes_speech import router as speech_router
from src.api.routes_triage import router as triage_router
from src.storage.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Rural Triage Kiosk", version="0.2.0", lifespan=lifespan)

# Offline kiosk: frontend runs on localhost too, allow it
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(triage_router, prefix="/triage", tags=["triage"])
app.include_router(pdf_router, prefix="/pdf", tags=["pdf"])
app.include_router(speech_router, prefix="/speech", tags=["speech"])


@app.get("/health")
def health():
    return {"status": "ok"}
