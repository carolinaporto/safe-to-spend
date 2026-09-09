"""Consumption-spending queries.

"Spending" is my own consumption: ``kind == expense`` outflows. Transfers,
adjustments (transfer legs), income and reimbursements are never counted
(invariants 6-8). For a shared expense, the slices belonging to other people
are subtracted (invariant 8). Gifts on external cards count in the category
*report* but not in the budget/pace (spec 4.4).
"""

import datetime as dt
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.category import Category
from backend.models.enums import (
    CategoryNature,
    TransactionDirection,
    TransactionKind,
)
from backend.models.expense_share import ExpenseShare
from backend.models.transaction import Transaction
from backend.money import ZERO, money

_MONTH = func.to_char(Transaction.date, "YYYY-MM-01")
_SUM = func.coalesce(func.sum(Transaction.amount_usd), 0)
_SHARE_SUM = func.coalesce(func.sum(ExpenseShare.share_amount_usd), 0)


def _expense_where(*, exclude_from_budget_only: bool):
    conds = [
        Transaction.kind == TransactionKind.expense,
        Transaction.direction == TransactionDirection.out.value,
    ]
    if exclude_from_budget_only:
        conds.append(Transaction.excluded_from_my_budget.is_(False))
    return tuple(conds)


def _shares_query(date_from: dt.date, date_to: dt.date):
    """Slices of shared expenses that belong to *other people* (money owed to
    me), scoped to a date range. Works on my own accounts and on someone
    else's card alike — the roommate slices of a purchase on Dad's card are
    still not my consumption. My own liability slices (``i_owe``) are not
    subtracted; that part I did consume."""
    return (
        select(Transaction.category_id, _SHARE_SUM)
        .join(ExpenseShare, ExpenseShare.transaction_id == Transaction.id)
        .where(
            Transaction.kind == TransactionKind.expense,
            ExpenseShare.i_owe.is_(False),
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by(Transaction.category_id)
    )


def _others_shares_by_category(
    db: Session, date_from: dt.date, date_to: dt.date
) -> dict[int | None, Decimal]:
    rows = db.execute(_shares_query(date_from, date_to)).all()
    return {cid: money(amount) for cid, amount in rows}


def total_consumption(
    db: Session,
    date_from: dt.date,
    date_to: dt.date,
    *,
    exclude_setup: bool = False,
    exclude_recurring: bool = False,
) -> Decimal:
    stmt = select(_SUM).where(
        *_expense_where(exclude_from_budget_only=True),
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
    if exclude_recurring:
        # Recurring bills are reserved from `available` up front (spec 4.5),
        # so they must not also count against the monthly pace.
        stmt = stmt.where(Transaction.recurring_id.is_(None))
    gross = money(db.scalar(stmt) or ZERO)
    others = sum(
        _others_shares_by_category(db, date_from, date_to).values(), ZERO
    )
    return money(gross - others)


def by_category(
    db: Session,
    date_from: dt.date,
    date_to: dt.date,
    *,
    for_report: bool = False,
) -> list[tuple[int | None, Decimal]]:
    stmt = (
        select(Transaction.category_id, _SUM)
        .where(
            *_expense_where(exclude_from_budget_only=not for_report),
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by(Transaction.category_id)
    )
    gross = {cid: money(a) for cid, a in db.execute(stmt).all()}
    for cid, share in _others_shares_by_category(db, date_from, date_to).items():
        if cid in gross:
            gross[cid] = money(gross[cid] - share)
    return [(cid, amount) for cid, amount in gross.items()]


def by_category_and_month(
    db: Session, date_from: dt.date, date_to: dt.date
) -> list[tuple[str, int | None, Decimal]]:
    stmt = (
        select(_MONTH, Transaction.category_id, _SUM)
        .where(
            *_expense_where(exclude_from_budget_only=False),
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by(_MONTH, Transaction.category_id)
        .order_by(_MONTH)
    )
    share_stmt = (
        select(_MONTH, Transaction.category_id, _SHARE_SUM)
        .join(ExpenseShare, ExpenseShare.transaction_id == Transaction.id)
        .where(
            Transaction.kind == TransactionKind.expense,
            ExpenseShare.i_owe.is_(False),
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by(_MONTH, Transaction.category_id)
    )
    shares = {(m, cid): money(a) for m, cid, a in db.execute(share_stmt).all()}
    out = []
    for m, cid, amount in db.execute(stmt).all():
        net = money(amount) - shares.get((m, cid), ZERO)
        out.append((m, cid, money(net)))
    return out


def spend_by_nature_and_month(
    db: Session, date_from: dt.date, date_to: dt.date
) -> list[tuple[str, str, Decimal]]:
    stmt = (
        select(_MONTH, func.coalesce(Category.nature, "uncategorized"), _SUM)
        .join(Category, Category.id == Transaction.category_id, isouter=True)
        .where(
            *_expense_where(exclude_from_budget_only=False),
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
    """Average daily *flexible* consumption over the trailing window (for
    runway). Setup and recurring bills are handled separately."""
    start = today - dt.timedelta(days=window_days)
    total = total_consumption(
        db, start, today, exclude_setup=True, exclude_recurring=True
    )
    return money(total / Decimal(window_days))
