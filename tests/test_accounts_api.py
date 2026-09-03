import datetime as dt
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.enums import (
    AccountKind,
    Currency,
    TransactionDirection,
    TransactionKind,
)
from backend.models.transaction import Transaction

NEW_ACCOUNT = {
    "name": "Chase Checking",
    "institution": "Chase",
    "kind": "checking",
    "currency": "USD",
    "opening_balance": "500.00",
    "opening_date": "2025-08-15",
}


def test_list_requires_auth(api_client: TestClient) -> None:
    assert api_client.get("/api/accounts").status_code == 401


def test_create_and_list_account(
    api_client: TestClient, auth_headers: dict
) -> None:
    created = api_client.post(
        "/api/accounts", json=NEW_ACCOUNT, headers=auth_headers
    )
    assert created.status_code == 201
    body = created.json()
    assert body["opening_balance"] == "500.00"
    assert body["balance"] == "500.00"
    assert body["balance_usd"] == "500.00"
    assert body["is_owned"] is True

    listed = api_client.get("/api/accounts", headers=auth_headers).json()
    assert [a["name"] for a in listed] == ["Chase Checking"]


def test_balance_reflects_transactions(
    api_client: TestClient, auth_headers: dict, db: Session
) -> None:
    account = Account(
        name="Wise USD",
        institution="Wise",
        kind=AccountKind.checking,
        currency=Currency.USD,
        opening_balance=Decimal("100.00"),
        opening_date=dt.date(2025, 8, 1),
    )
    db.add(account)
    db.flush()
    db.add(
        Transaction(
            date=dt.date(2025, 9, 1),
            account_id=account.id,
            direction=TransactionDirection.out,
            kind=TransactionKind.expense,
            amount=Decimal("40.00"),
            currency="USD",
            fx_rate_to_usd=Decimal("1"),
            amount_usd=Decimal("40.00"),
        )
    )
    db.flush()

    listed = api_client.get("/api/accounts", headers=auth_headers).json()
    assert listed[0]["balance"] == "60.00"


def test_delete_blocked_in_demo_mode(
    api_client: TestClient, auth_headers: dict, db: Session, demo_mode
) -> None:
    account = Account(
        name="X",
        institution="Y",
        kind=AccountKind.cash,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2025, 8, 1),
    )
    db.add(account)
    db.flush()
    resp = api_client.delete(
        f"/api/accounts/{account.id}", headers=auth_headers
    )
    assert resp.status_code == 403


def test_delete_conflicts_when_transactions_exist(
    api_client: TestClient, auth_headers: dict, db: Session
) -> None:
    account = Account(
        name="X",
        institution="Y",
        kind=AccountKind.cash,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2025, 8, 1),
    )
    db.add(account)
    db.flush()
    db.add(
        Transaction(
            date=dt.date(2025, 9, 1),
            account_id=account.id,
            direction=TransactionDirection.out,
            kind=TransactionKind.expense,
            amount=Decimal("1.00"),
            currency="USD",
            fx_rate_to_usd=Decimal("1"),
            amount_usd=Decimal("1.00"),
        )
    )
    db.flush()

    resp = api_client.delete(
        f"/api/accounts/{account.id}", headers=auth_headers
    )
    assert resp.status_code == 409


def test_delete_empty_account_succeeds(
    api_client: TestClient, auth_headers: dict, db: Session
) -> None:
    account = Account(
        name="Temp",
        institution="Y",
        kind=AccountKind.cash,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2025, 8, 1),
    )
    db.add(account)
    db.flush()
    resp = api_client.delete(
        f"/api/accounts/{account.id}", headers=auth_headers
    )
    assert resp.status_code == 204
