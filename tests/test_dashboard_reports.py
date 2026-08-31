import datetime as dt
import uuid
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
from backend.models.plan_config import PLAN_CONFIG_ID, PlanConfig
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


def _txn(db, account, *, kind, direction, amount, on, category=None, group=None):
    db.add(
        Transaction(
            date=on,
            account_id=account.id,
            direction=direction,
            kind=kind,
            amount=Decimal(amount),
            currency="USD",
            fx_rate_to_usd=Decimal("1"),
            amount_usd=Decimal(amount),
            category_id=category.id if category else None,
            transfer_group_id=group,
        )
    )
    db.flush()


def test_overview_serialises_money_as_strings(
    api_client: TestClient, auth_headers: dict, account: Account
) -> None:
    body = api_client.get(
        "/api/dashboard/overview", headers=auth_headers
    ).json()
    assert isinstance(body["daily_allowance_usd"], str)
    assert body["traffic_light"] in {"green", "warning", "danger"}
    assert isinstance(body["month_progress"]["total_days"], int)


def test_by_category_excludes_transfers_and_adjustments(
    api_client: TestClient,
    auth_headers: dict,
    account: Account,
    groceries: Category,
    db: Session,
) -> None:
    today = dt.date.today()
    _txn(
        db,
        account,
        kind=TransactionKind.expense,
        direction=TransactionDirection.out,
        amount="80.00",
        on=today,
        category=groceries,
    )
    # a transfer leg + an adjustment must not show up in category spending
    _txn(
        db,
        account,
        kind=TransactionKind.transfer,
        direction=TransactionDirection.out,
        amount="500.00",
        on=today,
        category=groceries,
        group=uuid.uuid4(),
    )
    _txn(
        db,
        account,
        kind=TransactionKind.adjustment,
        direction=TransactionDirection.out,
        amount="300.00",
        on=today,
        category=groceries,
    )

    body = api_client.get(
        "/api/dashboard/by-category", headers=auth_headers
    ).json()
    rows = {r["name"]: r["amount_usd"] for r in body["categories"]}
    assert rows == {"Groceries": "80.00"}


def test_by_category_grouped_by_month(
    api_client: TestClient,
    auth_headers: dict,
    account: Account,
    groceries: Category,
    db: Session,
) -> None:
    _txn(
        db,
        account,
        kind=TransactionKind.expense,
        direction=TransactionDirection.out,
        amount="40.00",
        on=dt.date(2026, 6, 3),
        category=groceries,
    )
    _txn(
        db,
        account,
        kind=TransactionKind.expense,
        direction=TransactionDirection.out,
        amount="55.00",
        on=dt.date(2026, 7, 9),
        category=groceries,
    )
    body = api_client.get(
        "/api/dashboard/by-category?from=2026-06-01&to=2026-07-31&group=month",
        headers=auth_headers,
    ).json()
    months = {m["month"]: m["categories"][0]["amount_usd"] for m in body["months"]}
    assert months == {"2026-06-01": "40.00", "2026-07-01": "55.00"}


def test_cashflow_returns_a_row_per_month(
    api_client: TestClient, auth_headers: dict, account: Account
) -> None:
    body = api_client.get(
        "/api/dashboard/cashflow?months=3", headers=auth_headers
    ).json()
    assert len(body["months"]) == 3


def test_projection_flags_a_zero_crossing_when_broke(
    api_client: TestClient, auth_headers: dict, db: Session
) -> None:
    poor = Account(
        name="Tiny",
        institution="x",
        kind=AccountKind.checking,
        currency=Currency.USD,
        opening_balance=Decimal("300.00"),
        opening_date=dt.date(2026, 1, 1),
    )
    groc = Category(name="Groceries", nature=CategoryNature.essential)
    db.add_all([poor, groc])
    db.flush()
    db.add(
        PlanConfig(
            id=PLAN_CONFIG_ID,
            academic_year_start=dt.date(2026, 1, 1),
            academic_year_end=dt.date.today() + dt.timedelta(days=120),
            emergency_reserve_usd=Decimal("0"),
            committed_costs=[],
        )
    )
    for i in range(1, 25):
        _txn(
            db,
            poor,
            kind=TransactionKind.expense,
            direction=TransactionDirection.out,
            amount="30.00",
            on=dt.date.today() - dt.timedelta(days=i),
            category=groc,
        )
    db.flush()

    body = api_client.get(
        "/api/dashboard/projection", headers=auth_headers
    ).json()
    assert body["zero_crossing_date"] is not None
    assert len(body["points"]) >= 2
