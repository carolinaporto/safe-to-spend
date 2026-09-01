"""Income / funding summary (spec section 6, Income screen)."""

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import Currency, TransactionKind
from backend.models.transaction import Transaction
from backend.models.transfer import Transfer
from backend.money import ZERO, money
from backend.services.balances import balance_in_usd, native_balances

FUNDING = "Funding"


def income_summary(db: Session) -> dict:
    today = dt.date.today()

    funding_cat = db.execute(
        select(Category.id).where(Category.name == FUNDING)
    ).scalar_one_or_none()

    entries = list(
        db.execute(
            select(Transaction)
            .where(
                Transaction.kind == TransactionKind.income,
                (
                    Transaction.category_id == funding_cat
                    if funding_cat is not None
                    else Transaction.category_id.is_(None)
                ),
            )
            .order_by(Transaction.date)
        ).scalars()
    )

    total_brl = money(
        sum(
            (e.amount for e in entries if e.currency == Currency.BRL.value),
            ZERO,
        )
    )
    total_usd = money(sum((e.amount_usd for e in entries), ZERO))

    converted_brl = money(
        db.scalar(
            select(func.coalesce(func.sum(Transfer.amount_out), 0)).where(
                Transfer.currency_out == Currency.BRL.value
            )
        )
        or ZERO
    )
    converted_usd = money(
        db.scalar(
            select(func.coalesce(func.sum(Transfer.amount_in), 0)).where(
                Transfer.currency_out == Currency.BRL.value,
                Transfer.currency_in == Currency.USD.value,
            )
        )
        or ZERO
    )
    fx_cost = money(
        db.scalar(
            select(func.coalesce(func.sum(Transfer.fx_cost_usd), 0)).where(
                Transfer.currency_out == Currency.BRL.value
            )
        )
        or ZERO
    )

    native = native_balances(db, today)
    brl_accounts = db.execute(
        select(Account).where(Account.currency == Currency.BRL.value)
    ).scalars()
    still_brl = money(
        sum((native.get(a.id, ZERO) for a in brl_accounts), ZERO)
    )
    still_brl_usd = balance_in_usd(db, Currency.BRL.value, still_brl, today)

    return {
        "total_funding_brl": total_brl,
        "total_funding_usd": total_usd,
        "converted_brl": converted_brl,
        "converted_usd": converted_usd,
        "still_in_brl": still_brl,
        "still_in_brl_usd": still_brl_usd,
        "cumulative_fx_cost_usd": fx_cost,
        "entries": [
            {
                "id": e.id,
                "date": e.date,
                "account_id": e.account_id,
                "amount": e.amount,
                "currency": e.currency,
                "amount_usd": e.amount_usd,
            }
            for e in entries
        ],
    }
