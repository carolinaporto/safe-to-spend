"""Brute-force protection for the login endpoint.

Failed attempts are counted per client IP within a sliding window. Once the
limit is reached the IP is locked out until the window passes. Only attempt
metadata (IP, timestamp, success flag) is stored — never the password.
"""

import math
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.login_attempt import LoginAttempt

settings = get_settings()


def client_ip(request: Request) -> str:
    """Best-effort client IP, honouring the proxy header Vercel sets."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _window_start() -> datetime:
    return datetime.now(UTC) - timedelta(minutes=settings.login_lockout_minutes)


def enforce_not_locked_out(db: Session, ip: str) -> None:
    since = _window_start()
    rows = db.scalars(
        select(LoginAttempt.created_at)
        .where(
            LoginAttempt.ip == ip,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.created_at >= since,
        )
        .order_by(LoginAttempt.created_at)
    ).all()

    if len(rows) < settings.login_max_failures:
        return

    oldest = rows[0]
    if oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=UTC)
    unlock_at = oldest + timedelta(minutes=settings.login_lockout_minutes)
    retry_after = max(1, math.ceil((unlock_at - datetime.now(UTC)).total_seconds()))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many failed login attempts. Try again later.",
        headers={"Retry-After": str(retry_after)},
    )


def record_attempt(db: Session, ip: str, *, succeeded: bool) -> None:
    db.add(LoginAttempt(ip=ip, succeeded=succeeded))
    if succeeded:
        # Clear the failure streak for this IP on a successful login.
        db.query(LoginAttempt).filter(
            LoginAttempt.ip == ip,
            LoginAttempt.succeeded.is_(False),
        ).delete(synchronize_session=False)
    db.commit()
