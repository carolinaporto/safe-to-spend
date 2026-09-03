from fastapi import APIRouter, Depends
from sqlalchemy import text

from backend.database import engine
from backend.deps import require_cron_secret

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    """Liveness only — is the function up. No infra details for the public."""
    return {"status": "ok"}


@router.get("/api/health/db", dependencies=[Depends(require_cron_secret)])
def health_db() -> dict:
    """Readiness — checks the database. Guarded so it isn't an info leak."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": True}
    except Exception:
        return {"status": "degraded", "database": False}
