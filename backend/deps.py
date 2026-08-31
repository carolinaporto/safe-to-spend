from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import get_settings
from backend.security import decode_access_token

import jwt

_bearer = HTTPBearer(auto_error=True)


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
