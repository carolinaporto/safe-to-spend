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
from backend.services.dates import add_months, month_end, month_start
from backend.services.spending import by_category, total_consumption

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


def _budgets_for_month(db: Session, month: dt.date) -> dict[int | None, Budget]:
    return {
        b.category_id: b
        for b in db.execute(
            select(Budget).where(Budget.month == month)
        ).scalars()
    }


def get_month_budget(db: Session, month: dt.date) -> list[BudgetLine]:
    per_category, total_spend = _spent_for_month(db, month)
    budgets = _budgets_for_month(db, month)
    categories = {
        c.id: c
        for c in db.execute(
            select(Category).where(
                Category.is_archived.is_(False),
                Category.nature.in_(BUDGETABLE_NATURES),
            )
        ).scalars()
    }

    # Previous month's numbers are needed only if something rolls over — and
    # then they are the same for every line, so fetch them at most once.
    prev_budgets: dict[int | None, Budget] = {}
    prev_cat_spend: dict[int | None, Decimal] = {}
    prev_total_spend = ZERO
    if any(b.rollover for b in budgets.values()):
        prev = add_months(month, -1)
        prev_budgets = _budgets_for_month(db, prev)
        prev_cat_spend, prev_total_spend = _spent_for_month(db, prev)

    def roll_in(category_id: int | None, enabled: bool) -> Decimal:
        if not enabled or category_id not in prev_budgets:
            return ZERO
        spent = (
            prev_total_spend
            if category_id is None
            else prev_cat_spend.get(category_id, ZERO)
        )
        return money(
            max(ZERO, money(prev_budgets[category_id].amount_usd) - spent)
        )

    def line(
        category_id: int | None, name: str, nature: str | None, spent: Decimal
    ) -> BudgetLine:
        budget = budgets.get(category_id)
        amount = money(budget.amount_usd) if budget else ZERO
        rollover = bool(budget and budget.rollover)
        carried = roll_in(category_id, rollover)
        return BudgetLine(
            category_id=category_id,
            name=name,
            nature=nature,
            amount_usd=amount,
            rollover=rollover,
            rollover_in_usd=carried,
            spent_usd=spent,
            remaining_usd=money(amount + carried - spent),
        )

    lines = [line(None, "Monthly ceiling", None, total_spend)]
    for cid, category in sorted(
        categories.items(), key=lambda kv: (kv[1].nature.value, kv[1].name)
    ):
        lines.append(
            line(
                cid,
                category.name,
                category.nature.value,
                per_category.get(cid, ZERO),
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
