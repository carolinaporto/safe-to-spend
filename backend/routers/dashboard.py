import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import require_auth
from backend.models.account import Account
from backend.models.category import Category
from backend.money import ZERO, money, money_str
from backend.schemas.common import ApiModel, MoneyStr
from backend.services.balances import balance_in_usd, native_balances
from backend.services.runway import (
    compute_overview,
    get_plan_config,
    net_worth_usd,
)
from backend.services.spending import (
    add_months,
    by_category,
    by_category_and_month,
    income_by_month,
    month_start,
    spend_by_nature_and_month,
    trailing_daily_burn,
)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_auth)],
)

NATURES = ["essential", "discretionary", "setup", "fee", "uncategorized"]


# ------------------------------------------------------------------ balances

class AccountBalance(ApiModel):
    id: int
    name: str
    institution: str
    currency: str
    kind: str
    is_owned: bool
    balance: MoneyStr
    balance_usd: MoneyStr


class BalancesOut(ApiModel):
    net_worth_usd: MoneyStr
    accounts: list[AccountBalance]


@router.get("/balances", response_model=BalancesOut)
def balances(db: Session = Depends(get_db)) -> BalancesOut:
    native = native_balances(db)
    accounts = (
        db.execute(select(Account).order_by(Account.sort_order, Account.name))
        .scalars()
        .all()
    )
    rows: list[AccountBalance] = []
    net_worth = ZERO
    for account in accounts:
        bal = native.get(account.id, ZERO)
        usd = balance_in_usd(db, account.currency.value, bal)
        rows.append(
            AccountBalance(
                id=account.id,
                name=account.name,
                institution=account.institution,
                currency=account.currency.value,
                kind=account.kind.value,
                is_owned=account.is_owned,
                balance=bal,
                balance_usd=usd,
            )
        )
        if account.is_owned:
            net_worth += usd
    return BalancesOut(net_worth_usd=money_str(net_worth), accounts=rows)


# ------------------------------------------------------------------ overview

class MonthProgress(ApiModel):
    elapsed_days: int
    total_days: int


class OverviewOut(ApiModel):
    as_of: dt.date
    academic_year_end: dt.date
    net_worth_usd: MoneyStr
    emergency_reserve_usd: MoneyStr
    future_committed_costs_usd: MoneyStr
    available_usd: MoneyStr
    months_remaining: str
    monthly_ceiling_usd: MoneyStr
    mtd_spend_usd: MoneyStr
    remaining_month_usd: MoneyStr
    days_remaining_in_month: int
    daily_allowance_usd: MoneyStr
    projected_month_end_spend_usd: MoneyStr
    traffic_light: str
    runway_days: int | None
    month_progress: MonthProgress


@router.get("/overview", response_model=OverviewOut)
def overview(db: Session = Depends(get_db)) -> OverviewOut:
    result = compute_overview(db)
    db.commit()  # persist a default plan_config if it was just created
    total_days = (
        result.days_remaining_in_month + result.as_of.day - 1
    )
    return OverviewOut(
        as_of=result.as_of,
        academic_year_end=result.academic_year_end,
        net_worth_usd=result.net_worth_usd,
        emergency_reserve_usd=result.emergency_reserve_usd,
        future_committed_costs_usd=result.future_committed_costs_usd,
        available_usd=result.available_usd,
        months_remaining=format(result.months_remaining, "f"),
        monthly_ceiling_usd=result.monthly_ceiling_usd,
        mtd_spend_usd=result.mtd_spend_usd,
        remaining_month_usd=result.remaining_month_usd,
        days_remaining_in_month=result.days_remaining_in_month,
        daily_allowance_usd=result.daily_allowance_usd,
        projected_month_end_spend_usd=result.projected_month_end_spend_usd,
        traffic_light=result.traffic_light,
        runway_days=result.runway_days,
        month_progress=MonthProgress(
            elapsed_days=result.as_of.day, total_days=total_days
        ),
    )


# --------------------------------------------------------------- by-category

class CategorySpend(ApiModel):
    category_id: int | None
    name: str
    nature: str | None
    color: str
    amount_usd: MoneyStr


class CategoryMonth(ApiModel):
    month: str
    categories: list[CategorySpend]


class ByCategoryOut(ApiModel):
    date_from: dt.date
    date_to: dt.date
    categories: list[CategorySpend] | None = None
    months: list[CategoryMonth] | None = None


def _category_lookup(db: Session) -> dict[int, Category]:
    return {c.id: c for c in db.execute(select(Category)).scalars()}


def _spend_row(cid: int | None, amount: Decimal, cats: dict) -> CategorySpend:
    category = cats.get(cid) if cid is not None else None
    return CategorySpend(
        category_id=cid,
        name=category.name if category else "Uncategorized",
        nature=category.nature.value if category else None,
        color=category.color if category else "",
        amount_usd=amount,
    )


@router.get("/by-category", response_model=ByCategoryOut)
def by_category_endpoint(
    date_from: dt.date | None = Query(default=None, alias="from"),
    date_to: dt.date | None = Query(default=None, alias="to"),
    group: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ByCategoryOut:
    today = dt.date.today()
    date_from = date_from or month_start(today)
    date_to = date_to or today
    cats = _category_lookup(db)

    if group == "month":
        buckets: dict[str, list[CategorySpend]] = {}
        for m, cid, amount in by_category_and_month(db, date_from, date_to):
            buckets.setdefault(m[:10], []).append(_spend_row(cid, amount, cats))
        months = [
            CategoryMonth(month=m, categories=rows)
            for m, rows in sorted(buckets.items())
        ]
        return ByCategoryOut(
            date_from=date_from, date_to=date_to, months=months
        )

    rows = [
        _spend_row(cid, amount, cats)
        for cid, amount in by_category(db, date_from, date_to)
    ]
    rows.sort(key=lambda r: r.amount_usd, reverse=True)
    return ByCategoryOut(
        date_from=date_from, date_to=date_to, categories=rows
    )


# ------------------------------------------------------------------ cashflow

class CashflowMonth(ApiModel):
    month: str
    essential: MoneyStr
    discretionary: MoneyStr
    setup: MoneyStr
    fee: MoneyStr
    uncategorized: MoneyStr
    total_spend: MoneyStr
    income: MoneyStr


class CashflowOut(ApiModel):
    months: list[CashflowMonth]


@router.get("/cashflow", response_model=CashflowOut)
def cashflow(
    months: int = Query(default=12, ge=1, le=36),
    db: Session = Depends(get_db),
) -> CashflowOut:
    today = dt.date.today()
    start = add_months(month_start(today), -(months - 1))

    spend: dict[str, dict[str, Decimal]] = {}
    for m, nature, amount in spend_by_nature_and_month(db, start, today):
        spend.setdefault(m[:10], {})[nature] = amount
    income = {k[:10]: v for k, v in income_by_month(db, start, today).items()}

    out: list[CashflowMonth] = []
    cursor = start
    while cursor <= today:
        key = cursor.isoformat()
        by_nature = spend.get(key, {})
        total = sum(by_nature.values(), ZERO)
        out.append(
            CashflowMonth(
                month=key,
                essential=by_nature.get("essential", ZERO),
                discretionary=by_nature.get("discretionary", ZERO),
                setup=by_nature.get("setup", ZERO),
                fee=by_nature.get("fee", ZERO),
                uncategorized=by_nature.get("uncategorized", ZERO),
                total_spend=money(total),
                income=income.get(key, ZERO),
            )
        )
        cursor = add_months(cursor, 1)
    return CashflowOut(months=out)


# ---------------------------------------------------------------- projection

class ProjectionPoint(ApiModel):
    date: dt.date
    balance_usd: MoneyStr


class ProjectionCost(ApiModel):
    due_date: dt.date
    label: str
    amount_usd: MoneyStr


class ProjectionOut(ApiModel):
    points: list[ProjectionPoint]
    committed_costs: list[ProjectionCost]
    daily_burn_usd: MoneyStr
    zero_crossing_date: dt.date | None


@router.get("/projection", response_model=ProjectionOut)
def projection(db: Session = Depends(get_db)) -> ProjectionOut:
    today = dt.date.today()
    config = get_plan_config(db)
    db.commit()

    burn = trailing_daily_burn(db, today)
    balance = net_worth_usd(db, today)

    costs_by_date: dict[dt.date, Decimal] = {}
    cost_rows: list[ProjectionCost] = []
    for item in config.committed_costs or []:
        due = item.get("due_date")
        if not due:
            continue
        due_date = dt.date.fromisoformat(due)
        amount = money(item.get("amount_usd", "0"))
        if due_date >= today:
            costs_by_date[due_date] = costs_by_date.get(due_date, ZERO) + amount
            cost_rows.append(
                ProjectionCost(
                    due_date=due_date,
                    label=item.get("label", ""),
                    amount_usd=amount,
                )
            )

    points: list[ProjectionPoint] = []
    zero_crossing: dt.date | None = None
    cursor = today
    step = 7
    while cursor <= config.academic_year_end:
        points.append(
            ProjectionPoint(date=cursor, balance_usd=money(balance))
        )
        for i in range(step):
            day = cursor + dt.timedelta(days=i + 1)
            balance -= burn
            balance -= costs_by_date.get(day, ZERO)
            if zero_crossing is None and balance <= 0:
                zero_crossing = day
        cursor += dt.timedelta(days=step)

    if points and points[-1].date < config.academic_year_end:
        points.append(
            ProjectionPoint(
                date=config.academic_year_end, balance_usd=money(balance)
            )
        )

    cost_rows.sort(key=lambda c: c.due_date)
    return ProjectionOut(
        points=points,
        committed_costs=cost_rows,
        daily_burn_usd=burn,
        zero_crossing_date=zero_crossing,
    )
