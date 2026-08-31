import datetime as dt
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import AccountKind, CategoryNature, Currency
from backend.models.fx_rate import FxRate


@pytest.fixture
def usd_account(db: Session) -> Account:
    account = Account(
        name="Wise USD",
        institution="Wise",
        kind=AccountKind.checking,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2025, 8, 1),
    )
    db.add(account)
    db.flush()
    return account


@pytest.fixture
def brl_account(db: Session) -> Account:
    account = Account(
        name="Wise BRL",
        institution="Wise",
        kind=AccountKind.checking,
        currency=Currency.BRL,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2025, 8, 1),
    )
    db.add(account)
    db.flush()
    return account


@pytest.fixture
def groceries(db: Session) -> Category:
    category = Category(name="Groceries", nature=CategoryNature.essential)
    db.add(category)
    db.flush()
    return category


def test_create_usd_expense_sets_direction_and_usd_amount(
    api_client: TestClient, auth_headers: dict, usd_account: Account
) -> None:
    resp = api_client.post(
        "/api/transactions",
        json={
            "account_id": usd_account.id,
            "kind": "expense",
            "amount": "12.50",
            "date": "2025-09-10",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["direction"] == "out"
    assert body["currency"] == "USD"
    assert body["fx_rate_to_usd"] == "1.00000000"
    assert body["amount_usd"] == "12.50"
    assert body["needs_review"] is False


def test_create_brl_expense_converts_at_write_time(
    api_client: TestClient,
    auth_headers: dict,
    brl_account: Account,
    db: Session,
) -> None:
    db.add(
        FxRate(
            date=dt.date(2025, 9, 10),
            base="BRL",
            quote="USD",
            rate=Decimal("0.18000000"),
            source="test",
        )
    )
    db.flush()

    resp = api_client.post(
        "/api/transactions",
        json={
            "account_id": brl_account.id,
            "kind": "expense",
            "amount": "100.00",
            "date": "2025-09-10",
        },
        headers=auth_headers,
    )
    body = resp.json()
    assert body["currency"] == "BRL"
    assert body["fx_rate_to_usd"] == "0.18000000"
    assert body["amount_usd"] == "18.00"


def test_brl_expense_without_a_rate_is_flagged_for_review(
    api_client: TestClient, auth_headers: dict, brl_account: Account
) -> None:
    resp = api_client.post(
        "/api/transactions",
        json={
            "account_id": brl_account.id,
            "kind": "expense",
            "amount": "100.00",
            "date": "2025-09-10",
        },
        headers=auth_headers,
    )
    assert resp.json()["needs_review"] is True


def test_patch_amount_recomputes_usd(
    api_client: TestClient, auth_headers: dict, usd_account: Account
) -> None:
    created = api_client.post(
        "/api/transactions",
        json={"account_id": usd_account.id, "kind": "expense", "amount": "10.00"},
        headers=auth_headers,
    ).json()

    patched = api_client.patch(
        f"/api/transactions/{created['id']}",
        json={"amount": "25.00"},
        headers=auth_headers,
    )
    assert patched.json()["amount_usd"] == "25.00"


def test_adjustment_requires_direction(
    api_client: TestClient, auth_headers: dict, usd_account: Account
) -> None:
    resp = api_client.post(
        "/api/transactions",
        json={
            "account_id": usd_account.id,
            "kind": "adjustment",
            "amount": "5.00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_list_filters_and_pagination(
    api_client: TestClient,
    auth_headers: dict,
    usd_account: Account,
    groceries: Category,
) -> None:
    for i in range(3):
        api_client.post(
            "/api/transactions",
            json={
                "account_id": usd_account.id,
                "kind": "expense",
                "amount": f"{i + 1}.00",
                "date": f"2025-09-1{i}",
                "category_id": groceries.id,
                "merchant_raw": "TRADER JOES" if i == 0 else "OTHER",
            },
            headers=auth_headers,
        )

    page = api_client.get(
        "/api/transactions?category=%d&page_size=2" % groceries.id,
        headers=auth_headers,
    ).json()
    assert page["total"] == 3
    assert len(page["items"]) == 2

    q = api_client.get(
        "/api/transactions?q=trader", headers=auth_headers
    ).json()
    assert q["total"] == 1

    by_nature = api_client.get(
        "/api/transactions?nature=essential", headers=auth_headers
    ).json()
    assert by_nature["total"] == 3


def test_needs_review_filter(
    api_client: TestClient,
    auth_headers: dict,
    brl_account: Account,
    usd_account: Account,
) -> None:
    # BRL with no rate -> flagged; USD -> not flagged
    api_client.post(
        "/api/transactions",
        json={"account_id": brl_account.id, "kind": "expense", "amount": "5.00"},
        headers=auth_headers,
    )
    api_client.post(
        "/api/transactions",
        json={"account_id": usd_account.id, "kind": "expense", "amount": "5.00"},
        headers=auth_headers,
    )
    flagged = api_client.get(
        "/api/transactions?needs_review=true", headers=auth_headers
    ).json()
    assert flagged["total"] == 1


def test_bulk_categorize(
    api_client: TestClient,
    auth_headers: dict,
    usd_account: Account,
    groceries: Category,
) -> None:
    ids = [
        api_client.post(
            "/api/transactions",
            json={
                "account_id": usd_account.id,
                "kind": "expense",
                "amount": "1.00",
            },
            headers=auth_headers,
        ).json()["id"]
        for _ in range(2)
    ]
    resp = api_client.post(
        "/api/transactions/bulk-categorize",
        json={"transaction_ids": ids, "category_id": groceries.id},
        headers=auth_headers,
    )
    assert resp.json()["updated"] == 2
    listed = api_client.get(
        f"/api/transactions?category={groceries.id}", headers=auth_headers
    ).json()
    assert listed["total"] == 2


def test_delete_blocked_in_demo(
    api_client: TestClient,
    auth_headers: dict,
    usd_account: Account,
    demo_mode,
) -> None:
    created = api_client.post(
        "/api/transactions",
        json={"account_id": usd_account.id, "kind": "expense", "amount": "1.00"},
        headers=auth_headers,
    ).json()
    resp = api_client.delete(
        f"/api/transactions/{created['id']}", headers=auth_headers
    )
    assert resp.status_code == 403


def test_csv_export(
    api_client: TestClient, auth_headers: dict, usd_account: Account
) -> None:
    api_client.post(
        "/api/transactions",
        json={
            "account_id": usd_account.id,
            "kind": "expense",
            "amount": "9.99",
            "description": "coffee",
        },
        headers=auth_headers,
    )
    resp = api_client.get("/api/transactions/export", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "amount_usd" in resp.text
    assert "9.99" in resp.text


def test_dashboard_balances_sums_owned_accounts_in_usd(
    api_client: TestClient,
    auth_headers: dict,
    usd_account: Account,
    brl_account: Account,
    db: Session,
) -> None:
    db.add(
        FxRate(
            date=dt.date.today(),
            base="BRL",
            quote="USD",
            rate=Decimal("0.20000000"),
            source="test",
        )
    )
    usd_account.opening_balance = Decimal("100.00")
    brl_account.opening_balance = Decimal("1000.00")
    db.flush()

    body = api_client.get(
        "/api/dashboard/balances", headers=auth_headers
    ).json()
    # 100 USD + (1000 BRL * 0.20) = 300.00
    assert body["net_worth_usd"] == "300.00"
