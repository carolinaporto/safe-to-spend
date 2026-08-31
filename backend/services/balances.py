"""Account balances — always computed, never stored (spec invariant 5).

    balance_native = opening_balance + Σ(inflows) − Σ(outflows)
    balance_usd    = balance_native converted to USD at today's rate
"""

import datetime as dt
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.enums import TransactionDirection
from backend.models.transaction import Transaction
from backend.money import ZERO, money
from backend.services.fx import convert_to_usd


def _signed_movement(db: Session, as_of: dt.date) -> dict[int, Decimal]:
    signed = func.sum(
        case(
            (
                Transaction.direction == TransactionDirection.in_.value,
                Transaction.amount,
            ),
            else_=-Transaction.amount,
        )
    )
    rows = db.execute(
        select(Transaction.account_id, signed)
        .where(Transaction.date <= as_of)
        .group_by(Transaction.account_id)
    ).all()
    return {account_id: total for account_id, total in rows}


def native_balances(
    db: Session, as_of: dt.date | None = None
) -> dict[int, Decimal]:
    """Balance per account as of ``as_of`` (default today). Future-dated
    transactions are not counted — expected income never inflates a balance."""
    as_of = as_of or dt.date.today()
    movement = _signed_movement(db, as_of)
    accounts = db.execute(select(Account)).scalars().all()
    return {
        account.id: money(account.opening_balance + movement.get(account.id, ZERO))
        for account in accounts
    }


def account_balance_native(db: Session, account_id: int) -> Decimal:
    return native_balances(db).get(account_id, ZERO)


def balance_in_usd(
    db: Session,
    currency: str,
    native_balance: Decimal,
    on_date: dt.date | None = None,
) -> Decimal:
    return convert_to_usd(
        db, native_balance, currency, on_date or dt.date.today()
    ).amount_usd
