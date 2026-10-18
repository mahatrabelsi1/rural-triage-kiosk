"""Runtime settings read from the environment (and app/backend/.env if present)."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"

# Demo accounts used only when STAFF_ACCOUNTS is not configured. Change them
# for any real deployment.
DEFAULT_STAFF_ACCOUNTS = "nurse:nurse2026:Nurse on duty,doctor:doctor2026:Duty clinician"


def load_env_file(path: Path = ENV_FILE) -> None:
    """Minimal .env reader: KEY=VALUE lines, # comments; real env vars win."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def staff_accounts() -> dict[str, dict[str, str]]:
    """Parse STAFF_ACCOUNTS="user:password[:Display name],..." into a dict."""
    accounts: dict[str, dict[str, str]] = {}
    for entry in os.getenv("STAFF_ACCOUNTS", DEFAULT_STAFF_ACCOUNTS).split(","):
        parts = entry.strip().split(":", 2)
        if len(parts) < 2 or not parts[0] or not parts[1]:
            continue
        username, password = parts[0].strip(), parts[1].strip()
        display = parts[2].strip() if len(parts) == 3 and parts[2].strip() else username
        accounts[username.lower()] = {"username": username, "password": password, "display_name": display}
    return accounts


ENABLE_HF_NER = env_flag("ENABLE_HF_NER", True)
HF_NER_MODEL_NAME = os.getenv("HF_NER_MODEL_NAME", "d4data/biomedical-ner-all")
TTS_MODEL_NAME = os.getenv("TTS_MODEL_NAME", "facebook/mms-tts-eng")
STT_MODEL_NAME = os.getenv("STT_MODEL_NAME", "openai/whisper-tiny")
# Empty = auto-detect language (e.g. Arabic, French, English). Set e.g. "en" to force one.
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "").strip()
AUTH_SECRET = os.getenv("AUTH_SECRET", "")
TOKEN_TTL_MINUTES = int(os.getenv("TOKEN_TTL_MINUTES", "480"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
