"""Full-database JSON snapshot for the weekly backup job (spec section 9)."""

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.category import Category
from backend.models.fx_rate import FxRate
from backend.models.person import Person
from backend.models.transaction import Transaction

_MODELS = {
    "accounts": Account,
    "categories": Category,
    "people": Person,
    "fx_rates": FxRate,
    "transactions": Transaction,
}


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return value


def build_snapshot(db: Session) -> dict:
    generated_at = dt.datetime.now(dt.UTC).isoformat()
    tables: dict[str, list[dict]] = {}
    for name, model in _MODELS.items():
        rows = db.execute(select(model)).scalars().all()
        tables[name] = [
            {c.name: _serialize(getattr(row, c.name)) for c in model.__table__.columns}
            for row in rows
        ]
    return {
        "generated_at": generated_at,
        "counts": {name: len(rows) for name, rows in tables.items()},
        "tables": tables,
    }
