"""Consumption-spending queries.

"Spending" here means my own consumption: ``kind == expense`` outflows that
are not excluded from my budget. Transfers, adjustments (the transfer legs),
income and reimbursements are never counted (spec invariants 6-8).
"""

import calendar
import datetime as dt
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.category import Category
from backend.models.enums import CategoryNature, TransactionKind
from backend.models.transaction import Transaction
from backend.money import ZERO, money


def month_start(d: dt.date) -> dt.date:
    return d.replace(day=1)


def month_end(d: dt.date) -> dt.date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def add_months(d: dt.date, n: int) -> dt.date:
    index = d.year * 12 + (d.month - 1) + n
    return dt.date(index // 12, index % 12 + 1, 1)


# Conditions that define a transaction as my consumption spending.
def _consumption_where():
    return (
        Transaction.kind == TransactionKind.expense,
        Transaction.excluded_from_my_budget.is_(False),
    )


_MONTH = func.to_char(Transaction.date, "YYYY-MM-01")
_SUM = func.coalesce(func.sum(Transaction.amount_usd), 0)


def total_consumption(
    db: Session,
    date_from: dt.date,
    date_to: dt.date,
    *,
    exclude_setup: bool = False,
) -> Decimal:
    stmt = select(_SUM).where(
        *_consumption_where(),
        Transaction.date >= date_from,
        Transaction.date <= date_to,
    )
    if exclude_setup:
        setup_ids = select(Category.id).where(
            Category.nature == CategoryNature.setup
        )
        stmt = stmt.where(
            Transaction.category_id.is_(None)
            | Transaction.category_id.notin_(setup_ids)
        )
    return money(db.scalar(stmt) or ZERO)


def by_category(
    db: Session, date_from: dt.date, date_to: dt.date
) -> list[tuple[int | None, Decimal]]:
    stmt = (
        select(Transaction.category_id, _SUM)
        .where(
            *_consumption_where(),
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by(Transaction.category_id)
    )
    return [(cid, money(amount)) for cid, amount in db.execute(stmt).all()]


def by_category_and_month(
    db: Session, date_from: dt.date, date_to: dt.date
) -> list[tuple[str, int | None, Decimal]]:
    stmt = (
        select(_MONTH, Transaction.category_id, _SUM)
        .where(
            *_consumption_where(),
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by(_MONTH, Transaction.category_id)
        .order_by(_MONTH)
    )
    return [(m, cid, money(a)) for m, cid, a in db.execute(stmt).all()]


def spend_by_nature_and_month(
    db: Session, date_from: dt.date, date_to: dt.date
) -> list[tuple[str, str, Decimal]]:
    stmt = (
        select(_MONTH, func.coalesce(Category.nature, "uncategorized"), _SUM)
        .join(Category, Category.id == Transaction.category_id, isouter=True)
        .where(
            *_consumption_where(),
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by(_MONTH, Category.nature)
        .order_by(_MONTH)
    )
    return [(m, nature, money(a)) for m, nature, a in db.execute(stmt).all()]


def income_by_month(
    db: Session, date_from: dt.date, date_to: dt.date
) -> dict[str, Decimal]:
    stmt = (
        select(_MONTH, _SUM)
        .where(
            Transaction.kind == TransactionKind.income,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by(_MONTH)
    )
    return {m: money(a) for m, a in db.execute(stmt).all()}


def trailing_daily_burn(
    db: Session, today: dt.date, window_days: int = 30
) -> Decimal:
    """Average daily consumption over the trailing window (for runway)."""
    start = today - dt.timedelta(days=window_days)
    total = total_consumption(db, start, today, exclude_setup=True)
    return money(total / Decimal(window_days))
