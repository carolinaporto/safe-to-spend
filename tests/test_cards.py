import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.enums import (
    AccountKind,
    Currency,
    TransactionDirection,
    TransactionKind,
)
from backend.models.transaction import Transaction
from backend.services.cards import card_panels


@pytest.fixture
def amex(db: Session) -> Account:
    a = Account(
        name="Amex",
        institution="Amex",
        kind=AccountKind.credit_card,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2026, 1, 1),
        statement_day=3,
        due_day=25,
    )
    db.add(a)
    db.flush()
    return a


def _charge(db, account, amount, on):
    db.add(
        Transaction(
            date=on,
            account_id=account.id,
            direction=TransactionDirection.out,
            kind=TransactionKind.expense,
            amount=Decimal(amount),
            currency="USD",
            fx_rate_to_usd=Decimal("1"),
            amount_usd=Decimal(amount),
        )
    )
    db.flush()


def test_panel_splits_current_balance_from_closed_statement(
    db: Session, amex: Account
) -> None:
    _charge(db, amex, "200.00", dt.date(2026, 7, 20))  # before Aug 3 close
    _charge(db, amex, "80.00", dt.date(2026, 8, 10))  # after close, still open

    [panel] = card_panels(db, dt.date(2026, 8, 22))
    assert panel.current_balance_usd == Decimal("280.00")
    assert panel.statement_close_date == dt.date(2026, 8, 3)
    assert panel.statement_balance_usd == Decimal("200.00")
    assert panel.due_date == dt.date(2026, 8, 25)
    assert panel.days_until_due == 3


def test_alert_fires_within_five_days_of_due_with_a_balance(
    db: Session, amex: Account
) -> None:
    _charge(db, amex, "150.00", dt.date(2026, 7, 20))
    [panel] = card_panels(db, dt.date(2026, 8, 22))
    assert panel.alert is True


def test_no_alert_when_statement_is_zero(db: Session, amex: Account) -> None:
    _charge(db, amex, "60.00", dt.date(2026, 8, 10))  # after close only
    [panel] = card_panels(db, dt.date(2026, 8, 22))
    assert panel.statement_balance_usd == Decimal("0.00")
    assert panel.alert is False


def test_cards_endpoint_returns_panels(api_client, auth_headers, amex) -> None:
    resp = api_client.get("/api/dashboard/cards", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Amex"
