"""Currency conversion against stored ``fx_rates`` (spec section 4.1).

A BRL amount converts to USD using the rate for the transaction date, falling
back to the most recent prior rate. All arithmetic is Decimal.
"""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.models.fx_rate import FxRate
from backend.money import ONE, money
from backend.money import rate as quantize_rate

USD = "USD"


@dataclass(frozen=True)
class Conversion:
    rate: Decimal  # units of quote per 1 unit of base
    amount_usd: Decimal
    stale: bool  # no exact-date rate was available


def get_rate(
    db: Session, on_date: dt.date, base: str, quote: str
) -> Decimal | None:
    """Rate for ``base -> quote`` on ``on_date``.

    Exact date if present, else the most recent earlier date, else the
    inverse of a ``quote -> base`` rate, else ``None``.
    """
    if base == quote:
        return ONE

    prior = db.execute(
        select(FxRate.rate)
        .where(
            FxRate.base == base,
            FxRate.quote == quote,
            FxRate.date <= on_date,
        )
        .order_by(FxRate.date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if prior is not None:
        return prior

    inverse = db.execute(
        select(FxRate.rate)
        .where(
            FxRate.base == quote,
            FxRate.quote == base,
            FxRate.date <= on_date,
        )
        .order_by(FxRate.date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if inverse is not None and inverse != 0:
        return quantize_rate(ONE / inverse)

    return None


def _has_exact_rate(
    db: Session, on_date: dt.date, base: str, quote: str
) -> bool:
    return (
        db.execute(
            select(FxRate.date).where(
                FxRate.date == on_date,
                FxRate.base == base,
                FxRate.quote == quote,
            )
        ).first()
        is not None
    )


def upsert_rate(
    db: Session,
    on_date: dt.date,
    base: str,
    quote: str,
    value: Decimal,
    source: str,
) -> None:
    stmt = pg_insert(FxRate).values(
        date=on_date,
        base=base,
        quote=quote,
        rate=quantize_rate(value),
        source=source,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["date", "base", "quote"],
        set_={"rate": stmt.excluded.rate, "source": stmt.excluded.source},
    )
    db.execute(stmt)


def convert_to_usd(
    db: Session, amount: Decimal, currency: str, on_date: dt.date
) -> Conversion:
    if currency == USD:
        return Conversion(rate=ONE, amount_usd=money(amount), stale=False)

    r = get_rate(db, on_date, currency, USD)
    if r is None:
        # Nothing to go on — record at parity and let the caller flag it.
        return Conversion(rate=ONE, amount_usd=money(amount), stale=True)

    stale = not _has_exact_rate(db, on_date, currency, USD)
    return Conversion(rate=r, amount_usd=money(amount * r), stale=stale)
