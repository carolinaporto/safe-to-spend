from fastapi import APIRouter
from sqlalchemy import text

from backend.database import engine

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
