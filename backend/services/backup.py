"""Full-database JSON snapshot for the weekly backup job (spec section 9)."""

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import LEDGER_MODELS


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dt.date | dt.datetime):
        return value.isoformat()
    return value


def build_snapshot(db: Session) -> dict:
    tables: dict[str, list[dict]] = {}
    # Reverse of the wipe order → parents before children.
    for model in reversed(LEDGER_MODELS):
        rows = db.execute(select(model)).scalars().all()
        tables[model.__tablename__] = [
            {c.name: _serialize(getattr(row, c.name)) for c in model.__table__.columns}
            for row in rows
        ]
    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "counts": {name: len(rows) for name, rows in tables.items()},
        "tables": tables,
    }
