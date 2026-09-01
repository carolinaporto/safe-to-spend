"""Runway and safe-to-spend (spec section 4.5).

    net_worth_usd    = Σ owned-account balances (BRL at today's rate)
    available        = net_worth_usd − emergency_reserve − future_committed_costs
    monthly_ceiling  = available / months_remaining
    mtd_spend        = Σ this month's consumption (setup excluded from the pace)
    daily_allowance  = (monthly_ceiling − mtd_spend) / days_left_in_month

Receivables, credit-card statements and owed liabilities are Phase 4; until
then net worth already reflects negative credit-card balances directly.
"""

import calendar
import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.models.plan_config import PLAN_CONFIG_ID, PlanConfig
from backend.money import ZERO, money, to_decimal
from backend.services.balances import account_balances, net_worth
from backend.services.spending import (
    month_end,
    month_start,
    total_consumption,
    trailing_daily_burn,
)

DAYS_PER_MONTH = Decimal("30.4375")
MIN_MONTHS_REMAINING = Decimal("0.1")


def get_plan_config(db: Session) -> PlanConfig:
    config = db.get(PlanConfig, PLAN_CONFIG_ID)
    if config is None:
        today = dt.date.today()
        config = PlanConfig(
            id=PLAN_CONFIG_ID,
            academic_year_start=today,
            academic_year_end=today + dt.timedelta(days=270),
            emergency_reserve_usd=ZERO,
            committed_costs=[],
        )
        db.add(config)
        db.flush()
    return config


def future_committed_costs(
    config: PlanConfig, today: dt.date
) -> Decimal:
    total = ZERO
    for item in config.committed_costs or []:
        due = item.get("due_date")
        if due and dt.date.fromisoformat(due) >= today:
            total += to_decimal(item.get("amount_usd", "0"))
    return money(total)


def net_worth_usd(db: Session, on_date: dt.date) -> Decimal:
    return net_worth(account_balances(db, as_of=on_date))


@dataclass
class Overview:
    as_of: dt.date
    academic_year_end: dt.date
    net_worth_usd: Decimal
    emergency_reserve_usd: Decimal
    future_committed_costs_usd: Decimal
    available_usd: Decimal
    months_remaining: Decimal
    monthly_ceiling_usd: Decimal
    mtd_spend_usd: Decimal
    remaining_month_usd: Decimal
    days_remaining_in_month: int
    daily_allowance_usd: Decimal
    projected_month_end_spend_usd: Decimal
    traffic_light: str
    runway_days: int | None


def _traffic_light(projected: Decimal, ceiling: Decimal) -> str:
    if ceiling <= 0:
        return "danger" if projected > 0 else "warning"
    ratio = projected / ceiling
    if ratio <= Decimal("1.0"):
        return "green"
    if ratio <= Decimal("1.1"):
        return "warning"
    return "danger"


def compute_overview(db: Session, today: dt.date | None = None) -> Overview:
    today = today or dt.date.today()
    config = get_plan_config(db)

    nw = net_worth_usd(db, today)
    reserve = money(config.emergency_reserve_usd)
    committed = future_committed_costs(config, today)
    available = money(nw - reserve - committed)

    days_to_end = max(0, (config.academic_year_end - today).days)
    months_remaining = max(
        MIN_MONTHS_REMAINING, Decimal(days_to_end) / DAYS_PER_MONTH
    )
    monthly_ceiling = money(available / months_remaining)

    mtd = total_consumption(
        db, month_start(today), today, exclude_setup=True
    )
    remaining_month = money(monthly_ceiling - mtd)

    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_remaining_in_month = (month_end(today) - today).days + 1
    daily_allowance = money(
        remaining_month / Decimal(days_remaining_in_month)
    )

    days_elapsed = today.day
    projected = (
        money(mtd / Decimal(days_elapsed) * Decimal(days_in_month))
        if days_elapsed
        else mtd
    )

    burn = trailing_daily_burn(db, today)
    runway_days = (
        max(0, int(available / burn)) if burn > 0 else None
    )

    return Overview(
        as_of=today,
        academic_year_end=config.academic_year_end,
        net_worth_usd=nw,
        emergency_reserve_usd=reserve,
        future_committed_costs_usd=committed,
        available_usd=available,
        months_remaining=months_remaining.quantize(Decimal("0.01")),
        monthly_ceiling_usd=monthly_ceiling,
        mtd_spend_usd=mtd,
        remaining_month_usd=remaining_month,
        days_remaining_in_month=days_remaining_in_month,
        daily_allowance_usd=daily_allowance,
        projected_month_end_spend_usd=projected,
        traffic_light=_traffic_light(projected, monthly_ceiling),
        runway_days=runway_days,
    )
