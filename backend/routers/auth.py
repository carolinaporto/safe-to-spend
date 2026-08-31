from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.deps import require_auth
from backend.security import create_access_token, verify_password
from backend.services.login_throttle import (
    client_ip,
    enforce_not_locked_out,
    record_attempt,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    ip = client_ip(request)
    enforce_not_locked_out(db, ip)

    if not verify_password(body.password, settings.app_password_hash):
        record_attempt(db, ip, succeeded=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    record_attempt(db, ip, succeeded=True)
    return TokenResponse(access_token=create_access_token())


@router.get("/me")
def me(subject: str = Depends(require_auth)) -> dict:
    return {"subject": subject}
