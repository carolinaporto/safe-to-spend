"""Recurring rules: templates that generate transactions on a schedule."""

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.enums import (
    TransactionDirection,
    TransactionKind,
    TransactionSource,
)
from backend.models.recurring_rule import RecurringRule
from backend.models.transaction import Transaction
from backend.services.dates import add_months, clamp_day
from backend.services.fx import convert_to_usd


def occurrences(
    rule: RecurringRule, since: dt.date, until: dt.date
) -> list[dt.date]:
    start = max(rule.start_date, since)
    end = min(rule.end_date, until) if rule.end_date else until
    if start > end:
        return []

    out: list[dt.date] = []
    if rule.frequency.value == "weekly":
        # anchored on start_date's weekday
        delta = (start - rule.start_date).days % 7
        cursor = start if delta == 0 else start + dt.timedelta(days=7 - delta)
        while cursor <= end:
            out.append(cursor)
            cursor += dt.timedelta(days=7)
    elif rule.frequency.value == "monthly":
        month = dt.date(start.year, start.month, 1)
        while month <= end:
            occ = clamp_day(month.year, month.month, rule.day_of_month)
            if since <= occ <= end and occ >= rule.start_date:
                out.append(occ)
            month = add_months(month, 1)
    else:  # yearly
        year = start.year
        while dt.date(year, 1, 1) <= end:
            occ = clamp_day(year, rule.start_date.month, rule.start_date.day)
            if since <= occ <= end and occ >= rule.start_date:
                out.append(occ)
            year += 1
    return sorted(o for o in out if o >= since and o <= end)


def generate_for_rule(
    db: Session, rule: RecurringRule, until: dt.date
) -> int:
    since = (
        rule.last_generated_date + dt.timedelta(days=1)
        if rule.last_generated_date
        else rule.start_date
    )
    created = 0
    kind = (
        TransactionKind.income if rule.is_income else TransactionKind.expense
    )
    direction = (
        TransactionDirection.in_ if rule.is_income else TransactionDirection.out
    )
    for occ in occurrences(rule, since, until):
        conversion = convert_to_usd(db, rule.amount, rule.currency, occ)
        db.add(
            Transaction(
                date=occ,
                account_id=rule.account_id,
                direction=direction,
                kind=kind,
                amount=rule.amount,
                currency=rule.currency,
                fx_rate_to_usd=conversion.rate,
                amount_usd=conversion.amount_usd,
                category_id=rule.category_id,
                merchant_clean=rule.name,
                description=f"Recurring: {rule.name}",
                source=TransactionSource.manual,
                recurring_id=rule.id,
                needs_review=rule.currency != "USD" and conversion.stale,
            )
        )
        created += 1
    rule.last_generated_date = until
    return created


def generate_due(db: Session, until: dt.date | None = None) -> dict:
    until = until or dt.date.today()
    rules = list(
        db.execute(
            select(RecurringRule).where(RecurringRule.auto_create.is_(True))
        ).scalars()
    )
    generated = sum(generate_for_rule(db, rule, until) for rule in rules)
    db.commit()
    return {"rules": len(rules), "generated": generated, "through": until.isoformat()}
