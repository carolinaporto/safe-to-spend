from fastapi import APIRouter

from backend.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/api/meta")
def meta() -> dict:
    """Public client configuration — safe to read before login."""
    settings = get_settings()
    return {
        "demo_mode": settings.demo_mode,
        # In demo mode the import screen is hidden and destructive actions
        # (delete, bulk edit, import commit) return 403.
        "import_enabled": not settings.demo_mode,
    }
