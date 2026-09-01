import datetime as dt
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import (
    AccountKind,
    CategoryNature,
    Currency,
    TransactionDirection,
    TransactionKind,
)
from backend.models.transaction import Transaction


@pytest.fixture
def account(db: Session) -> Account:
    a = Account(
        name="Chase",
        institution="Chase",
        kind=AccountKind.checking,
        currency=Currency.USD,
        opening_balance=Decimal("5000.00"),
        opening_date=dt.date(2026, 1, 1),
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def groceries(db: Session) -> Category:
    c = Category(name="Groceries", nature=CategoryNature.essential)
    db.add(c)
    db.flush()
    return c


def _spend(db, account, category, amount, on):
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
            category_id=category.id,
        )
    )
    db.flush()


def test_empty_month_returns_zeroed_lines(
    api_client: TestClient, auth_headers: dict, groceries: Category
) -> None:
    body = api_client.get("/api/budgets/2026-08", headers=auth_headers).json()
    assert body["lines"][0]["name"] == "Monthly ceiling"
    assert body["lines"][0]["amount_usd"] == "0.00"
    groc = next(bl for bl in body["lines"] if bl["name"] == "Groceries")
    assert groc["amount_usd"] == "0.00"


def test_put_then_get_shows_amount_spent_and_remaining(
    api_client: TestClient,
    auth_headers: dict,
    account: Account,
    groceries: Category,
    db: Session,
) -> None:
    _spend(db, account, groceries, "120.00", dt.date(2026, 8, 4))

    put = api_client.put(
        "/api/budgets/2026-08",
        headers=auth_headers,
        json={
            "entries": [
                {"category_id": None, "amount_usd": "2000.00", "rollover": False},
                {
                    "category_id": groceries.id,
                    "amount_usd": "400.00",
                    "rollover": False,
                },
            ]
        },
    )
    assert put.status_code == 200
    groc = next(bl for bl in put.json()["lines"] if bl["name"] == "Groceries")
    assert groc["amount_usd"] == "400.00"
    assert groc["spent_usd"] == "120.00"
    assert groc["remaining_usd"] == "280.00"


def test_put_is_blocked_in_demo_mode(
    api_client: TestClient, auth_headers: dict, demo_mode
) -> None:
    resp = api_client.put(
        "/api/budgets/2026-08",
        headers=auth_headers,
        json={"entries": []},
    )
    assert resp.status_code == 403


def test_copy_from_previous_month(
    api_client: TestClient, auth_headers: dict, groceries: Category
) -> None:
    api_client.put(
        "/api/budgets/2026-07",
        headers=auth_headers,
        json={
            "entries": [
                {
                    "category_id": groceries.id,
                    "amount_usd": "300.00",
                    "rollover": False,
                }
            ]
        },
    )
    copied = api_client.post(
        "/api/budgets/2026-08/copy-from-previous", headers=auth_headers
    )
    assert copied.status_code == 200
    groc = next(
        bl for bl in copied.json()["lines"] if bl["name"] == "Groceries"
    )
    assert groc["amount_usd"] == "300.00"


def test_copy_from_previous_404_when_nothing_to_copy(
    api_client: TestClient, auth_headers: dict
) -> None:
    resp = api_client.post(
        "/api/budgets/2026-08/copy-from-previous", headers=auth_headers
    )
    assert resp.status_code == 404


def test_rollover_carries_unspent_budget_forward(
    api_client: TestClient,
    auth_headers: dict,
    account: Account,
    groceries: Category,
    db: Session,
) -> None:
    # July: budget 300, spent 100 -> 200 unspent, rollover on
    _spend(db, account, groceries, "100.00", dt.date(2026, 7, 10))
    api_client.put(
        "/api/budgets/2026-07",
        headers=auth_headers,
        json={
            "entries": [
                {
                    "category_id": groceries.id,
                    "amount_usd": "300.00",
                    "rollover": True,
                }
            ]
        },
    )
    api_client.put(
        "/api/budgets/2026-08",
        headers=auth_headers,
        json={
            "entries": [
                {
                    "category_id": groceries.id,
                    "amount_usd": "300.00",
                    "rollover": True,
                }
            ]
        },
    )
    body = api_client.get("/api/budgets/2026-08", headers=auth_headers).json()
    groc = next(bl for bl in body["lines"] if bl["name"] == "Groceries")
    assert groc["rollover_in_usd"] == "200.00"
    assert groc["remaining_usd"] == "500.00"
