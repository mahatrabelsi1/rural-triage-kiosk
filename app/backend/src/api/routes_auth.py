from fastapi import APIRouter, Depends, HTTPException

from src.auth import authenticate, issue_token, require_staff
from src.triage.schemas import LoginRequest, LoginResponse

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    account = authenticate(req.username, req.password)
    if account is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token, expires_at = issue_token(account)
    return LoginResponse(
        token=token,
        username=account["username"],
        display_name=account["display_name"],
        expires_at=expires_at,
    )


@router.get("/me")
def me(claims: dict = Depends(require_staff)):
    return {"username": claims["sub"], "display_name": claims.get("name", claims["sub"]), "expires_at": claims["exp"]}
