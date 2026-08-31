import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.enums import (
    AccountKind,
    Currency,
    TransactionDirection,
    TransactionKind,
)
from backend.models.fx_rate import FxRate
from backend.models.transaction import Transaction
from backend.services.balances import balance_in_usd, native_balances


def _account(db: Session, currency: Currency, opening: str) -> Account:
    account = Account(
        name=f"{currency} acct",
        institution="Bank",
        kind=AccountKind.checking,
        currency=currency,
        opening_balance=Decimal(opening),
        opening_date=dt.date(2025, 8, 1),
    )
    db.add(account)
    db.flush()
    return account


def _txn(db: Session, account: Account, direction, amount: str) -> None:
    db.add(
        Transaction(
            date=dt.date(2025, 9, 1),
            account_id=account.id,
            direction=direction,
            kind=(
                TransactionKind.income
                if direction == TransactionDirection.in_
                else TransactionKind.expense
            ),
            amount=Decimal(amount),
            currency=account.currency.value,
            fx_rate_to_usd=Decimal("1"),
            amount_usd=Decimal(amount),
        )
    )
    db.flush()


def test_balance_is_opening_plus_inflows_minus_outflows(db: Session) -> None:
    account = _account(db, Currency.USD, "100.00")
    _txn(db, account, TransactionDirection.in_, "50.00")
    _txn(db, account, TransactionDirection.out, "30.00")
    _txn(db, account, TransactionDirection.out, "5.25")

    assert native_balances(db)[account.id] == Decimal("114.75")


def test_account_with_no_transactions_equals_opening(db: Session) -> None:
    account = _account(db, Currency.USD, "42.10")
    assert native_balances(db)[account.id] == Decimal("42.10")


def test_brl_balance_converts_to_usd_at_todays_rate(db: Session) -> None:
    account = _account(db, Currency.BRL, "1000.00")
    db.add(
        FxRate(
            date=dt.date.today(),
            base="BRL",
            quote="USD",
            rate=Decimal("0.20000000"),
            source="test",
        )
    )
    db.flush()

    native = native_balances(db)[account.id]
    assert native == Decimal("1000.00")
    assert balance_in_usd(db, "BRL", native) == Decimal("200.00")
