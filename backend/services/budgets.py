"""Monthly budgets and their consumption."""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models.budget import Budget
from backend.models.category import Category
from backend.models.enums import CategoryNature
from backend.money import ZERO, money
from backend.services.spending import (
    add_months,
    by_category,
    month_end,
    month_start,
    total_consumption,
)

BUDGETABLE_NATURES = (
    CategoryNature.essential,
    CategoryNature.discretionary,
    CategoryNature.setup,
    CategoryNature.fee,
)


def parse_month(value: str) -> dt.date:
    value = value.strip()
    parts = value.split("-")
    year, month = int(parts[0]), int(parts[1])
    return dt.date(year, month, 1)


@dataclass
class BudgetLine:
    category_id: int | None
    name: str
    nature: str | None
    amount_usd: Decimal
    rollover: bool
    rollover_in_usd: Decimal
    spent_usd: Decimal
    remaining_usd: Decimal


def _spent_for_month(
    db: Session, month: dt.date
) -> tuple[dict[int | None, Decimal], Decimal]:
    start, end = month_start(month), month_end(month)
    per_category = dict(by_category(db, start, end))
    total = total_consumption(db, start, end)
    return per_category, total


def _rollover_in(
    db: Session, month: dt.date, category_id: int | None, enabled: bool
) -> Decimal:
    if not enabled:
        return ZERO
    prev = add_months(month, -1)
    prev_budget = db.execute(
        select(Budget).where(
            Budget.month == prev,
            (
                Budget.category_id == category_id
                if category_id is not None
                else Budget.category_id.is_(None)
            ),
        )
    ).scalar_one_or_none()
    if prev_budget is None:
        return ZERO
    prev_spent, prev_total = _spent_for_month(db, prev)
    spent = prev_total if category_id is None else prev_spent.get(category_id, ZERO)
    return money(max(ZERO, money(prev_budget.amount_usd) - spent))


def get_month_budget(db: Session, month: dt.date) -> list[BudgetLine]:
    per_category, total_spend = _spent_for_month(db, month)
    budgets = {
        b.category_id: b
        for b in db.execute(
            select(Budget).where(Budget.month == month)
        ).scalars()
    }
    categories = {
        c.id: c
        for c in db.execute(
            select(Category).where(
                Category.is_archived.is_(False),
                Category.nature.in_(BUDGETABLE_NATURES),
            )
        ).scalars()
    }

    lines: list[BudgetLine] = []

    global_budget = budgets.get(None)
    global_amount = money(global_budget.amount_usd) if global_budget else ZERO
    global_rollover = bool(global_budget and global_budget.rollover)
    global_roll_in = _rollover_in(db, month, None, global_rollover)
    lines.append(
        BudgetLine(
            category_id=None,
            name="Monthly ceiling",
            nature=None,
            amount_usd=global_amount,
            rollover=global_rollover,
            rollover_in_usd=global_roll_in,
            spent_usd=total_spend,
            remaining_usd=money(global_amount + global_roll_in - total_spend),
        )
    )

    for cid, category in sorted(
        categories.items(), key=lambda kv: (kv[1].nature.value, kv[1].name)
    ):
        budget = budgets.get(cid)
        amount = money(budget.amount_usd) if budget else ZERO
        rollover = bool(budget and budget.rollover)
        roll_in = _rollover_in(db, month, cid, rollover)
        spent = per_category.get(cid, ZERO)
        lines.append(
            BudgetLine(
                category_id=cid,
                name=category.name,
                nature=category.nature.value,
                amount_usd=amount,
                rollover=rollover,
                rollover_in_usd=roll_in,
                spent_usd=spent,
                remaining_usd=money(amount + roll_in - spent),
            )
        )
    return lines


def put_month_budget(
    db: Session,
    month: dt.date,
    entries: list[tuple[int | None, Decimal, bool]],
) -> None:
    """Replace the whole month's budget set. Entries with amount 0 are dropped."""
    db.execute(delete(Budget).where(Budget.month == month))
    for category_id, amount, rollover in entries:
        if money(amount) <= 0:
            continue
        db.add(
            Budget(
                month=month,
                category_id=category_id,
                amount_usd=money(amount),
                rollover=rollover,
            )
        )
    db.commit()


def copy_from_previous(db: Session, month: dt.date) -> int:
    prev = add_months(month, -1)
    previous = db.execute(
        select(Budget).where(Budget.month == prev)
    ).scalars().all()
    if not previous:
        return 0
    db.execute(delete(Budget).where(Budget.month == month))
    for b in previous:
        db.add(
            Budget(
                month=month,
                category_id=b.category_id,
                amount_usd=b.amount_usd,
                rollover=b.rollover,
            )
        )
    db.commit()
    return len(previous)
