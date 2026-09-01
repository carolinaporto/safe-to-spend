import datetime as dt
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.enums import AccountKind, Currency, TransactionKind
from backend.models.fx_rate import FxRate
from backend.models.transaction import Transaction
from backend.services.balances import native_balances

TODAY = dt.date(2026, 9, 1)


@pytest.fixture
def accounts(db: Session) -> dict[str, Account]:
    rows = {
        "brl": Account(
            name="Wise BRL",
            institution="Wise",
            kind=AccountKind.checking,
            currency=Currency.BRL,
            opening_balance=Decimal("50000.00"),
            opening_date=dt.date(2026, 1, 1),
        ),
        "usd": Account(
            name="Chase",
            institution="Chase",
            kind=AccountKind.checking,
            currency=Currency.USD,
            opening_balance=Decimal("2000.00"),
            opening_date=dt.date(2026, 1, 1),
        ),
    }
    db.add_all(rows.values())
    db.flush()
    return rows


@pytest.fixture
def brl_rate(db: Session) -> None:
    db.add(
        FxRate(
            date=TODAY,
            base="BRL",
            quote="USD",
            rate=Decimal("0.18500000"),
            source="test",
        )
    )
    db.flush()


def _create(api_client, auth_headers, accounts, **overrides):
    body = {
        "date": TODAY.isoformat(),
        "from_account_id": accounts["brl"].id,
        "to_account_id": accounts["usd"].id,
        "amount_out": "5000.00",
        "amount_in": "890.00",
        "provider": "Wise",
    }
    body.update(overrides)
    return api_client.post("/api/transfers", json=body, headers=auth_headers)


def test_transfer_creates_exactly_two_legs_and_balances_reconcile(
    api_client: TestClient, auth_headers: dict, accounts, brl_rate, db: Session
) -> None:
    resp = _create(api_client, auth_headers, accounts)
    assert resp.status_code == 201

    legs = (
        db.query(Transaction)
        .filter(Transaction.kind == TransactionKind.transfer)
        .all()
    )
    assert len(legs) == 2
    assert {leg.transfer_group_id for leg in legs} == {legs[0].transfer_group_id}

    native = native_balances(db, TODAY)
    assert native[accounts["brl"].id] == Decimal("45000.00")  # 50000 − 5000
    assert native[accounts["usd"].id] == Decimal("2890.00")  # 2000 + 890


def test_fx_cost_is_market_value_out_minus_amount_in(
    api_client: TestClient, auth_headers: dict, accounts, brl_rate
) -> None:
    body = _create(api_client, auth_headers, accounts).json()
    # effective 890/5000 = 0.178; market 0.185
    assert body["effective_rate"] == "0.17800000"
    assert body["market_rate"] == "0.18500000"
    # 5000 * 0.185 = 925 theoretical USD in; got 890 -> 35.00 lost
    assert body["fx_cost_usd"] == "35.00"


def test_explicit_market_rate_overrides_lookup(
    api_client: TestClient, auth_headers: dict, accounts, brl_rate
) -> None:
    body = _create(
        api_client, auth_headers, accounts, market_rate="0.19000000"
    ).json()
    # 5000 * 0.19 = 950; got 890 -> 60.00
    assert body["fx_cost_usd"] == "60.00"


def test_same_currency_transfer_has_zero_fx_cost(
    api_client: TestClient, auth_headers: dict, accounts, db: Session
) -> None:
    other = Account(
        name="Cash",
        institution="Cash",
        kind=AccountKind.cash,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2026, 1, 1),
    )
    db.add(other)
    db.flush()
    body = api_client.post(
        "/api/transfers",
        json={
            "date": TODAY.isoformat(),
            "from_account_id": accounts["usd"].id,
            "to_account_id": other.id,
            "amount_out": "300.00",
            "amount_in": "300.00",
        },
        headers=auth_headers,
    ).json()
    assert body["fx_cost_usd"] == "0.00"
    assert body["market_rate"] == "1.00000000"


def test_transfer_legs_absent_from_category_spending(
    api_client: TestClient, auth_headers: dict, accounts, brl_rate
) -> None:
    _create(api_client, auth_headers, accounts)
    report = api_client.get(
        f"/api/dashboard/by-category?from={TODAY}&to={TODAY}", headers=auth_headers
    ).json()
    assert report["categories"] == []


def test_summary_aggregates_cost_and_providers(
    api_client: TestClient, auth_headers: dict, accounts, brl_rate
) -> None:
    _create(api_client, auth_headers, accounts)
    _create(api_client, auth_headers, accounts, amount_in="880.00")
    summary = api_client.get(
        "/api/transfers/summary", headers=auth_headers
    ).json()
    assert summary["count"] == 2
    assert summary["total_fx_cost_usd"] == "80.00"  # 35 + 45
    wise = next(p for p in summary["providers"] if p["provider"] == "Wise")
    assert wise["count"] == 2


def test_delete_removes_both_legs(
    api_client: TestClient, auth_headers: dict, accounts, brl_rate, db: Session
) -> None:
    tid = _create(api_client, auth_headers, accounts).json()["id"]
    resp = api_client.delete(f"/api/transfers/{tid}", headers=auth_headers)
    assert resp.status_code == 204
    assert (
        db.query(Transaction)
        .filter(Transaction.kind == TransactionKind.transfer)
        .count()
        == 0
    )


def test_same_account_rejected(
    api_client: TestClient, auth_headers: dict, accounts
) -> None:
    resp = _create(
        api_client,
        auth_headers,
        accounts,
        to_account_id=accounts["brl"].id,
    )
    assert resp.status_code == 422


def test_create_blocked_in_demo(
    api_client: TestClient, auth_headers: dict, accounts, brl_rate, demo_mode
) -> None:
    assert _create(api_client, auth_headers, accounts).status_code == 403
