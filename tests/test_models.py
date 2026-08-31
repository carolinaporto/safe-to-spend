import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import Account, Category, Transaction
from backend.models.enums import (
    AccountKind,
    CategoryNature,
    Currency,
    TransactionDirection,
    TransactionKind,
)


def _account(db: Session, **kw) -> Account:
    account = Account(
        name=kw.get("name", "Test"),
        institution="Test Bank",
        kind=kw.get("kind", AccountKind.checking),
        currency=kw.get("currency", Currency.USD),
        opening_balance=kw.get("opening_balance", Decimal("0.00")),
        opening_date=dt.date(2025, 8, 1),
    )
    db.add(account)
    db.flush()
    return account


def test_money_columns_round_trip_as_exact_decimals(db: Session) -> None:
    account = _account(db, opening_balance=Decimal("1234.56"))
    txn = Transaction(
        date=dt.date(2025, 9, 3),
        account_id=account.id,
        direction=TransactionDirection.out,
        kind=TransactionKind.expense,
        amount=Decimal("19.99"),
        currency="USD",
        fx_rate_to_usd=Decimal("1"),
        amount_usd=Decimal("19.99"),
    )
    db.add(txn)
    db.flush()
    db.expire_all()

    reloaded = db.get(Transaction, txn.id)
    assert isinstance(reloaded.amount, Decimal)
    assert isinstance(reloaded.amount_usd, Decimal)
    assert reloaded.amount == Decimal("19.99")
    assert db.get(Account, account.id).opening_balance == Decimal("1234.56")


def test_fx_rate_keeps_eight_decimal_places(db: Session) -> None:
    account = _account(db, currency=Currency.BRL)
    txn = Transaction(
        date=dt.date(2025, 9, 3),
        account_id=account.id,
        direction=TransactionDirection.out,
        kind=TransactionKind.expense,
        amount=Decimal("100.00"),
        currency="BRL",
        fx_rate_to_usd=Decimal("0.18543210"),
        amount_usd=Decimal("18.54"),
    )
    db.add(txn)
    db.flush()
    db.expire_all()

    assert db.get(Transaction, txn.id).fx_rate_to_usd == Decimal("0.18543210")


def test_direction_is_persisted_as_the_spec_value(db: Session) -> None:
    account = _account(db)
    txn = Transaction(
        date=dt.date(2025, 9, 3),
        account_id=account.id,
        direction=TransactionDirection.in_,
        kind=TransactionKind.income,
        amount=Decimal("50.00"),
        currency="USD",
        fx_rate_to_usd=Decimal("1"),
        amount_usd=Decimal("50.00"),
    )
    db.add(txn)
    db.flush()

    raw = db.execute(
        text("SELECT direction FROM transactions WHERE id = :i"),
        {"i": txn.id},
    ).scalar_one()
    assert raw == "in"


def test_ledger_date_is_a_plain_date(db: Session) -> None:
    account = _account(db)
    txn = Transaction(
        date=dt.date(2025, 9, 3),
        account_id=account.id,
        direction=TransactionDirection.out,
        kind=TransactionKind.expense,
        amount=Decimal("1.00"),
        currency="USD",
        fx_rate_to_usd=Decimal("1"),
        amount_usd=Decimal("1.00"),
    )
    db.add(txn)
    db.flush()
    db.expire_all()

    value = db.get(Transaction, txn.id).date
    assert type(value) is dt.date
    assert not isinstance(value, dt.datetime)


def test_transfer_group_id_round_trips_as_uuid(db: Session) -> None:
    account = _account(db)
    group = uuid.uuid4()
    for direction, kind_amount in ((TransactionDirection.out, "10.00"),):
        db.add(
            Transaction(
                date=dt.date(2025, 9, 3),
                account_id=account.id,
                direction=direction,
                kind=TransactionKind.transfer,
                amount=Decimal(kind_amount),
                currency="USD",
                fx_rate_to_usd=Decimal("1"),
                amount_usd=Decimal(kind_amount),
                transfer_group_id=group,
            )
        )
    db.flush()
    db.expire_all()

    rows = db.query(Transaction).filter_by(transfer_group_id=group).all()
    assert len(rows) == 1
    assert rows[0].transfer_group_id == group


def test_category_tree_via_parent_id(db: Session) -> None:
    parent = Category(name="Food", nature=CategoryNature.essential)
    db.add(parent)
    db.flush()
    child = Category(
        name="Groceries", nature=CategoryNature.essential, parent_id=parent.id
    )
    db.add(child)
    db.flush()
    db.expire_all()

    assert db.get(Category, child.id).parent_id == parent.id
