import datetime as dt
import json

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import require_auth, require_cron_secret
from backend.services.backup import build_snapshot

router = APIRouter(prefix="/api", tags=["backup"])


@router.get("/backup", dependencies=[Depends(require_auth)])
def download_backup(db: Session = Depends(get_db)) -> Response:
    snapshot = build_snapshot(db)
    stamp = dt.date.today().isoformat()
    return Response(
        content=json.dumps(snapshot, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f"attachment; filename=safe-to-spend-backup-{stamp}.json"
            )
        },
    )


@router.post("/cron/backup", dependencies=[Depends(require_cron_secret)])
def weekly_backup(db: Session = Depends(get_db)) -> dict:
    """Weekly job. Returns the snapshot so the scheduler can archive it."""
    return build_snapshot(db)
