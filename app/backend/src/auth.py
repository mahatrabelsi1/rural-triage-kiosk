"""Staff login for the clinician side of the kiosk.

Patients and companions use the intake flow without logging in. Anything that
exposes stored patient data (queue, session detail, PDF) requires a staff token.
Tokens are stateless HMAC-signed blobs, so no session table is needed.
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src import config

logger = logging.getLogger(__name__)

# Without AUTH_SECRET, a random key is used: tokens stop working after a restart,
# which is acceptable for a single kiosk and safer than a hardcoded default.
_SECRET = (config.AUTH_SECRET or secrets.token_urlsafe(32)).encode("utf-8")
if not config.AUTH_SECRET:
    logger.warning("AUTH_SECRET not set; staff tokens will be invalidated on restart.")

_bearer = HTTPBearer(auto_error=False)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> str:
    return _b64(hmac.new(_SECRET, body.encode("ascii"), hashlib.sha256).digest())


def authenticate(username: str, password: str) -> dict | None:
    account = config.staff_accounts().get(username.strip().lower())
    if account is None:
        # Compare anyway so response time doesn't reveal which usernames exist.
        hmac.compare_digest(password.encode("utf-8"), b"x" * len(password))
        return None
    if not hmac.compare_digest(password.encode("utf-8"), account["password"].encode("utf-8")):
        return None
    return account


def issue_token(account: dict, ttl_minutes: int | None = None) -> tuple[str, int]:
    expires_at = int(time.time()) + 60 * (ttl_minutes or config.TOKEN_TTL_MINUTES)
    body = _b64(json.dumps({"sub": account["username"], "name": account["display_name"], "exp": expires_at}).encode("utf-8"))
    return f"{body}.{_sign(body)}", expires_at


def verify_token(token: str) -> dict | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(body)):
        return None
    try:
        claims = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(claims.get("exp", 0)) < time.time():
        return None
    return claims


def require_staff(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    claims = verify_token(credentials.credentials) if credentials else None
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff login required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims
