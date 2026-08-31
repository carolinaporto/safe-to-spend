import hmac

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import get_settings
from backend.security import decode_access_token

import jwt

_bearer = HTTPBearer(auto_error=True)


def require_cron_secret(
    x_cron_secret: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Guard cron endpoints. Accepts ``X-Cron-Secret: <secret>`` or the
    ``Authorization: Bearer <secret>`` header that Vercel Cron sends."""
    expected = get_settings().cron_secret
    presented = x_cron_secret
    if presented is None and authorization and authorization.startswith("Bearer "):
        presented = authorization.removeprefix("Bearer ")
    if not expected or not presented or not hmac.compare_digest(presented, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cron secret",
        )


def deny_in_demo() -> None:
    """Block an endpoint when DEMO_MODE is on.

    Attach to destructive / mutating routes:
        @router.delete(..., dependencies=[Depends(deny_in_demo)])
    """
    if get_settings().demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is disabled in the demo.",
        )


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Validate the bearer token; returns the token subject."""
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload.get("sub", "owner")
