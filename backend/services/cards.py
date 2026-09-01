"""Credit-card statement view (spec 4.6).

Category spending is accrual (purchase date); this panel is the cash view —
current balance, the closed statement, and when it's due.
"""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.enums import AccountKind
from backend.money import ZERO, money
from backend.services.balances import balance_in_usd, native_balances
from backend.services.dates import clamp_day

ALERT_DAYS = 5


@dataclass
class CardPanel:
    account_id: int
    name: str
    currency: str
    current_balance_usd: Decimal  # amount owed now (positive)
    statement_balance_usd: Decimal  # owed as of the last statement close
    statement_close_date: dt.date | None
    due_date: dt.date | None
    days_until_due: int | None
    alert: bool


def _last_on_or_before(today: dt.date, day: int) -> dt.date:
    this_month = clamp_day(today.year, today.month, day)
    if this_month <= today:
        return this_month
    prev = today.replace(day=1) - dt.timedelta(days=1)
    return clamp_day(prev.year, prev.month, day)


def _next_after(anchor: dt.date, day: int) -> dt.date:
    same_month = clamp_day(anchor.year, anchor.month, day)
    if same_month > anchor:
        return same_month
    nxt = (anchor.replace(day=28) + dt.timedelta(days=7)).replace(day=1)
    return clamp_day(nxt.year, nxt.month, day)


def _owed_usd(db: Session, account: Account, on_date: dt.date) -> Decimal:
    """Positive = amount owed on the card as of ``on_date``."""
    native = native_balances(db, on_date).get(account.id, ZERO)
    return money(-balance_in_usd(db, account.currency.value, native, on_date))


def card_panels(db: Session, today: dt.date | None = None) -> list[CardPanel]:
    today = today or dt.date.today()
    accounts = (
        db.execute(
            select(Account)
            .where(Account.kind == AccountKind.credit_card)
            .order_by(Account.sort_order, Account.name)
        )
        .scalars()
        .all()
    )

    panels: list[CardPanel] = []
    for account in accounts:
        current = _owed_usd(db, account, today)

        close_date = due_date = None
        stmt_usd = ZERO
        days = None
        alert = False
        if account.statement_day:
            close_date = _last_on_or_before(today, account.statement_day)
            stmt_usd = _owed_usd(db, account, close_date)
            if account.due_day:
                due_date = _next_after(close_date, account.due_day)
                days = (due_date - today).days
                alert = 0 <= days <= ALERT_DAYS and stmt_usd > 0

        panels.append(
            CardPanel(
                account_id=account.id,
                name=account.name,
                currency=account.currency.value,
                current_balance_usd=current,
                statement_balance_usd=stmt_usd,
                statement_close_date=close_date,
                due_date=due_date,
                days_until_due=days,
                alert=alert,
            )
        )
    return panels
