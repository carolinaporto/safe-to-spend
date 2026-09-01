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
    PersonRole,
)
from backend.models.person import Person

TODAY = dt.date(2026, 9, 1)


@pytest.fixture
def people(db: Session) -> dict[str, Person]:
    rows = {
        "me": Person(name="You", role=PersonRole.me),
        "marina": Person(name="Marina", role=PersonRole.roommate),
        "dad": Person(name="Dad", role=PersonRole.parent),
    }
    db.add_all(rows.values())
    db.flush()
    return rows


@pytest.fixture
def chase(db: Session) -> Account:
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
def dads_card(db: Session, people) -> Account:
    a = Account(
        name="Dad's Card",
        institution="Dad",
        kind=AccountKind.external,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2026, 1, 1),
        owner_person_id=people["dad"].id,
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def rent(db: Session) -> Category:
    c = Category(name="Rent", nature=CategoryNature.essential)
    db.add(c)
    db.flush()
    return c


def test_shared_expense_reported_spend_is_amount_minus_others_shares(
    api_client: TestClient, auth_headers, people, chase, rent
) -> None:
    resp = api_client.post(
        "/api/transactions",
        json={
            "account_id": chase.id,
            "kind": "expense",
            "amount": "2850.00",
            "date": TODAY.isoformat(),
            "category_id": rent.id,
            "is_shared": True,
            "shares": [{"person_id": people["marina"].id, "share_amount_usd": "950.00"}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["is_shared"] is True

    report = api_client.get(
        f"/api/dashboard/by-category?from={TODAY}&to={TODAY}", headers=auth_headers
    ).json()
    rent_row = next(r for r in report["categories"] if r["category_id"] == rent.id)
    # 2850 − 950 = 1900 is my consumption
    assert rent_row["amount_usd"] == "1900.00"


def test_shares_exceeding_amount_rejected(
    api_client: TestClient, auth_headers, people, chase, rent
) -> None:
    resp = api_client.post(
        "/api/transactions",
        json={
            "account_id": chase.id,
            "kind": "expense",
            "amount": "100.00",
            "category_id": rent.id,
            "shares": [{"person_id": people["marina"].id, "share_amount_usd": "150.00"}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_external_owe_creates_a_liability_against_the_owner(
    api_client: TestClient, auth_headers, people, dads_card
) -> None:
    resp = api_client.post(
        "/api/transactions",
        json={
            "account_id": dads_card.id,
            "kind": "expense",
            "amount": "120.00",
            "external_treatment": "owe",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["shares"][0]["person_id"] == people["dad"].id

    balances = api_client.get("/api/people/balances", headers=auth_headers).json()
    dad = next(b for b in balances if b["person_id"] == people["dad"].id)
    assert dad["i_owe_usd"] == "120.00"
    assert dad["net_usd"] == "-120.00"

    overview = api_client.get("/api/dashboard/overview", headers=auth_headers).json()
    assert overview["liabilities_usd"] == "120.00"


def test_external_gift_counts_in_report_but_not_budget(
    api_client: TestClient, auth_headers, dads_card, rent
) -> None:
    api_client.post(
        "/api/transactions",
        json={
            "account_id": dads_card.id,
            "kind": "expense",
            "amount": "200.00",
            "date": TODAY.isoformat(),
            "category_id": rent.id,
            "external_treatment": "gift",
        },
        headers=auth_headers,
    )
    report = api_client.get(
        f"/api/dashboard/by-category?from={TODAY}&to={TODAY}", headers=auth_headers
    ).json()
    assert report["categories"][0]["amount_usd"] == "200.00"

    overview = api_client.get("/api/dashboard/overview", headers=auth_headers).json()
    assert overview["mtd_spend_usd"] == "0.00"  # gift excluded from pace


def test_external_purchase_needs_a_treatment(
    api_client: TestClient, auth_headers, dads_card
) -> None:
    resp = api_client.post(
        "/api/transactions",
        json={"account_id": dads_card.id, "kind": "expense", "amount": "10.00"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_settle_creates_linked_income_and_marks_shares_settled(
    api_client: TestClient, auth_headers, people, chase, rent, db: Session
) -> None:
    db.add(Category(name="Roommate reimbursement", nature=CategoryNature.income))
    db.flush()

    api_client.post(
        "/api/transactions",
        json={
            "account_id": chase.id,
            "kind": "expense",
            "amount": "2850.00",
            "category_id": rent.id,
            "shares": [{"person_id": people["marina"].id, "share_amount_usd": "950.00"}],
        },
        headers=auth_headers,
    )

    resp = api_client.post(
        f"/api/people/{people['marina'].id}/settle",
        json={"account_id": chase.id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["kind"] == "income"
    assert body["amount_usd"] == "950.00"

    balances = api_client.get("/api/people/balances", headers=auth_headers).json()
    marina = next(
        (b for b in balances if b["person_id"] == people["marina"].id), None
    )
    assert marina is None or marina["net_usd"] == "0.00"


def test_settle_nets_receivable_against_liability(
    api_client: TestClient, auth_headers, people, chase, dads_card, db: Session
) -> None:
    # Dad owes me 200 (shared, my account); I owe Dad 120 (his card)
    api_client.post(
        "/api/transactions",
        json={
            "account_id": chase.id,
            "kind": "expense",
            "amount": "500.00",
            "shares": [{"person_id": people["dad"].id, "share_amount_usd": "200.00"}],
        },
        headers=auth_headers,
    )
    api_client.post(
        "/api/transactions",
        json={
            "account_id": dads_card.id,
            "kind": "expense",
            "amount": "120.00",
            "external_treatment": "owe",
        },
        headers=auth_headers,
    )
    resp = api_client.post(
        f"/api/people/{people['dad'].id}/settle",
        json={"account_id": chase.id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["amount_usd"] == "80.00"  # 200 − 120


def test_settle_nothing_owed_is_rejected(
    api_client: TestClient, auth_headers, people, chase
) -> None:
    resp = api_client.post(
        f"/api/people/{people['marina'].id}/settle",
        json={"account_id": chase.id},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_settle_into_external_account_rejected(
    api_client: TestClient, auth_headers, people, chase, dads_card
) -> None:
    api_client.post(
        "/api/transactions",
        json={
            "account_id": chase.id,
            "kind": "expense",
            "amount": "500.00",
            "shares": [{"person_id": people["marina"].id, "share_amount_usd": "200.00"}],
        },
        headers=auth_headers,
    )
    resp = api_client.post(
        f"/api/people/{people['marina'].id}/settle",
        json={"account_id": dads_card.id},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_people_crud_and_demo_gating(
    api_client: TestClient, auth_headers
) -> None:
    created = api_client.post(
        "/api/people",
        json={"name": "Theo", "role": "roommate"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    pid = created.json()["id"]

    patched = api_client.patch(
        f"/api/people/{pid}", json={"notes": "apt 4B"}, headers=auth_headers
    )
    assert patched.json()["notes"] == "apt 4B"


def test_person_create_blocked_in_demo(
    api_client: TestClient, auth_headers, demo_mode
) -> None:
    resp = api_client.post(
        "/api/people", json={"name": "Nope"}, headers=auth_headers
    )
    assert resp.status_code == 403
