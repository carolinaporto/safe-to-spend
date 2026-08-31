import datetime as dt
from decimal import Decimal

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


def test_list_requires_auth(api_client: TestClient) -> None:
    assert api_client.get("/api/categories").status_code == 403


def test_create_category_and_subcategory(
    api_client: TestClient, auth_headers: dict
) -> None:
    parent = api_client.post(
        "/api/categories",
        json={"name": "Food", "nature": "essential"},
        headers=auth_headers,
    ).json()
    child = api_client.post(
        "/api/categories",
        json={
            "name": "Groceries",
            "nature": "essential",
            "parent_id": parent["id"],
        },
        headers=auth_headers,
    )
    assert child.status_code == 201
    assert child.json()["parent_id"] == parent["id"]


def test_archive_via_patch(api_client: TestClient, auth_headers: dict) -> None:
    cat = api_client.post(
        "/api/categories",
        json={"name": "Bars", "nature": "discretionary"},
        headers=auth_headers,
    ).json()
    patched = api_client.patch(
        f"/api/categories/{cat['id']}",
        json={"is_archived": True},
        headers=auth_headers,
    )
    assert patched.json()["is_archived"] is True

    active = api_client.get(
        "/api/categories?include_archived=false", headers=auth_headers
    ).json()
    assert all(c["name"] != "Bars" for c in active)


def test_delete_conflicts_when_used_by_a_transaction(
    api_client: TestClient, auth_headers: dict, db: Session
) -> None:
    category = Category(name="Rent", nature=CategoryNature.essential)
    account = Account(
        name="A",
        institution="B",
        kind=AccountKind.checking,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2025, 8, 1),
    )
    db.add_all([category, account])
    db.flush()
    db.add(
        Transaction(
            date=dt.date(2025, 9, 1),
            account_id=account.id,
            category_id=category.id,
            direction=TransactionDirection.out,
            kind=TransactionKind.expense,
            amount=Decimal("10.00"),
            currency="USD",
            fx_rate_to_usd=Decimal("1"),
            amount_usd=Decimal("10.00"),
        )
    )
    db.flush()

    resp = api_client.delete(
        f"/api/categories/{category.id}", headers=auth_headers
    )
    assert resp.status_code == 409


def test_delete_unused_category_succeeds(
    api_client: TestClient, auth_headers: dict, db: Session
) -> None:
    category = Category(name="Temp", nature=CategoryNature.setup)
    db.add(category)
    db.flush()
    resp = api_client.delete(
        f"/api/categories/{category.id}", headers=auth_headers
    )
    assert resp.status_code == 204
