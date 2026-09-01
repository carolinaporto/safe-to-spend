"""Transfers: two ledger legs + a metadata row with the FX cost (spec 4.2).

    effective_rate  = amount_in / amount_out
    market_rate     = fx_rates[date] for currency_out -> currency_in
    fx_cost_usd     = (amount_out * market_rate − amount_in) → USD

No expense row is created for the cost; the two legs already leave both
balances correct.
"""

import datetime as dt
import uuid
from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.enums import (
    TransactionDirection,
    TransactionKind,
    TransactionSource,
)
from backend.models.transaction import Transaction
from backend.models.transfer import Transfer
from backend.money import ONE, ZERO, money, rate, to_decimal
from backend.services.fx import convert_to_usd, get_rate


@dataclass
class TransferInput:
    date: dt.date
    from_account_id: int
    to_account_id: int
    amount_out: Decimal
    amount_in: Decimal
    currency_out: str | None = None  # defaults to from-account currency
    currency_in: str | None = None  # defaults to to-account currency
    explicit_fee: Decimal | None = None
    explicit_fee_currency: str | None = None
    market_rate: Decimal | None = None
    provider: str = ""
    notes: str = ""


def _account(db: Session, account_id: int, label: str) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"unknown {label}"
        )
    return account


def create_transfer(db: Session, data: TransferInput) -> Transfer:
    if data.from_account_id == data.to_account_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "from and to accounts must differ",
        )
    src = _account(db, data.from_account_id, "from_account_id")
    dst = _account(db, data.to_account_id, "to_account_id")

    currency_out = (data.currency_out or src.currency.value).upper()
    currency_in = (data.currency_in or dst.currency.value).upper()
    amount_out = money(data.amount_out)
    amount_in = money(data.amount_in)
    if amount_out <= 0 or amount_in <= 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "amounts must be positive"
        )

    group = uuid.uuid4()
    out_conv = convert_to_usd(db, amount_out, currency_out, data.date)
    in_conv = convert_to_usd(db, amount_in, currency_in, data.date)

    out_leg = Transaction(
        date=data.date,
        account_id=src.id,
        direction=TransactionDirection.out,
        kind=TransactionKind.transfer,
        amount=amount_out,
        currency=currency_out,
        fx_rate_to_usd=out_conv.rate,
        amount_usd=out_conv.amount_usd,
        transfer_group_id=group,
        source=TransactionSource.manual,
        description=f"Transfer to {dst.name}",
        merchant_clean=data.provider or "Transfer",
    )
    in_leg = Transaction(
        date=data.date,
        account_id=dst.id,
        direction=TransactionDirection.in_,
        kind=TransactionKind.transfer,
        amount=amount_in,
        currency=currency_in,
        fx_rate_to_usd=in_conv.rate,
        amount_usd=in_conv.amount_usd,
        transfer_group_id=group,
        source=TransactionSource.manual,
        description=f"Transfer from {src.name}",
        merchant_clean=data.provider or "Transfer",
    )

    effective_rate = rate(amount_in / amount_out)
    if data.market_rate is not None:
        market_rate = rate(data.market_rate)
    elif currency_out == currency_in:
        market_rate = ONE
    else:
        looked_up = get_rate(db, data.date, currency_out, currency_in)
        market_rate = rate(looked_up) if looked_up is not None else effective_rate

    theoretical_in = to_decimal(amount_out) * market_rate
    fx_cost_native = theoretical_in - amount_in  # in currency_in units
    fx_cost_usd = (
        money(fx_cost_native)
        if currency_in == "USD"
        else convert_to_usd(db, fx_cost_native, currency_in, data.date).amount_usd
    )

    transfer = Transfer(
        transfer_group_id=str(group),
        date=data.date,
        from_account_id=src.id,
        to_account_id=dst.id,
        amount_out=amount_out,
        currency_out=currency_out,
        amount_in=amount_in,
        currency_in=currency_in,
        explicit_fee=(
            money(data.explicit_fee) if data.explicit_fee is not None else None
        ),
        explicit_fee_currency=data.explicit_fee_currency,
        effective_rate=effective_rate,
        market_rate=market_rate,
        fx_cost_usd=fx_cost_usd,
        provider=data.provider,
        notes=data.notes,
    )
    db.add_all([out_leg, in_leg, transfer])
    db.commit()
    db.refresh(transfer)
    return transfer


def delete_transfer(db: Session, transfer: Transfer) -> None:
    db.query(Transaction).filter(
        Transaction.transfer_group_id == uuid.UUID(transfer.transfer_group_id)
    ).delete(synchronize_session=False)
    db.delete(transfer)
    db.commit()


def summary(db: Session) -> dict:
    transfers = list(db.execute(select(Transfer)).scalars())
    total_cost = money(sum((t.fx_cost_usd for t in transfers), ZERO))

    by_provider: dict[str, dict] = {}
    for t in transfers:
        key = t.provider or "—"
        bucket = by_provider.setdefault(
            key,
            {
                "provider": key,
                "count": 0,
                "fx_cost_usd": ZERO,
                "_out": ZERO,
                "_weighted": ZERO,
            },
        )
        bucket["count"] += 1
        bucket["fx_cost_usd"] += t.fx_cost_usd
        bucket["_out"] += t.amount_out
        bucket["_weighted"] += t.effective_rate * t.amount_out

    providers = []
    for bucket in by_provider.values():
        avg = (
            rate(bucket["_weighted"] / bucket["_out"])
            if bucket["_out"]
            else ZERO
        )
        providers.append(
            {
                "provider": bucket["provider"],
                "count": bucket["count"],
                "fx_cost_usd": money(bucket["fx_cost_usd"]),
                "avg_effective_rate": avg,
            }
        )

    return {
        "count": len(transfers),
        "total_fx_cost_usd": total_cost,
        "providers": sorted(providers, key=lambda p: -p["count"]),
    }
