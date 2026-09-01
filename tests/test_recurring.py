import datetime as dt
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.enums import (
    AccountKind,
    Currency,
    RecurringFrequency,
    TransactionKind,
)
from backend.models.recurring_rule import RecurringRule
from backend.models.transaction import Transaction
from backend.services.recurring import generate_for_rule, occurrences


@pytest.fixture
def account(db: Session) -> Account:
    a = Account(
        name="Chase",
        institution="Chase",
        kind=AccountKind.checking,
        currency=Currency.USD,
        opening_balance=Decimal("1000.00"),
        opening_date=dt.date(2026, 1, 1),
    )
    db.add(a)
    db.flush()
    return a


def _rule(account, **kw) -> RecurringRule:
    defaults = dict(
        name="Spotify",
        account_id=account.id,
        amount=Decimal("11.99"),
        currency="USD",
        frequency=RecurringFrequency.monthly,
        day_of_month=5,
        start_date=dt.date(2026, 1, 1),
    )
    defaults.update(kw)
    return RecurringRule(**defaults)


def test_monthly_occurrences_clamp_short_months() -> None:
    rule = _rule(
        type("A", (), {"id": 1})(),
        day_of_month=31,
        start_date=dt.date(2026, 1, 1),
    )
    occ = occurrences(rule, dt.date(2026, 1, 1), dt.date(2026, 3, 31))
    assert occ == [dt.date(2026, 1, 31), dt.date(2026, 2, 28), dt.date(2026, 3, 31)]


def test_weekly_occurrences_anchor_on_start_weekday() -> None:
    rule = _rule(
        type("A", (), {"id": 1})(),
        frequency=RecurringFrequency.weekly,
        start_date=dt.date(2026, 1, 5),  # Monday
    )
    occ = occurrences(rule, dt.date(2026, 1, 1), dt.date(2026, 2, 1))
    assert occ == [
        dt.date(2026, 1, 5),
        dt.date(2026, 1, 12),
        dt.date(2026, 1, 19),
        dt.date(2026, 1, 26),
    ]


def test_yearly_occurrences_on_start_month_day() -> None:
    rule = _rule(
        type("A", (), {"id": 1})(),
        frequency=RecurringFrequency.yearly,
        start_date=dt.date(2025, 3, 15),
    )
    occ = occurrences(rule, dt.date(2025, 1, 1), dt.date(2027, 1, 1))
    assert occ == [dt.date(2025, 3, 15), dt.date(2026, 3, 15)]


def test_generate_is_idempotent_via_last_generated_date(
    db: Session, account: Account
) -> None:
    rule = _rule(account, start_date=dt.date(2026, 6, 1))
    db.add(rule)
    db.flush()

    first = generate_for_rule(db, rule, dt.date(2026, 8, 15))
    db.flush()
    assert first == 3  # Jun 5, Jul 5, Aug 5
    assert rule.last_generated_date == dt.date(2026, 8, 15)

    again = generate_for_rule(db, rule, dt.date(2026, 8, 20))
    assert again == 0

    third = generate_for_rule(db, rule, dt.date(2026, 9, 10))
    assert third == 1  # only Sep 5

    txns = (
        db.query(Transaction)
        .filter(Transaction.recurring_id == rule.id)
        .all()
    )
    assert len(txns) == 4
    assert all(t.kind == TransactionKind.expense for t in txns)


def test_income_rule_generates_inflows(db: Session, account: Account) -> None:
    rule = _rule(
        account,
        name="TA stipend",
        amount=Decimal("430.00"),
        is_income=True,
        start_date=dt.date(2026, 6, 1),
        day_of_month=15,
    )
    db.add(rule)
    db.flush()
    generate_for_rule(db, rule, dt.date(2026, 7, 31))
    db.flush()
    txns = db.query(Transaction).filter(Transaction.recurring_id == rule.id).all()
    assert len(txns) == 2
    assert all(t.kind == TransactionKind.income for t in txns)


def test_rule_crud_and_run_endpoint(
    api_client: TestClient, auth_headers, account: Account
) -> None:
    created = api_client.post(
        "/api/recurring-rules",
        json={
            "name": "Rent",
            "account_id": account.id,
            "amount": "1300.00",
            "currency": "USD",
            "frequency": "monthly",
            "day_of_month": 1,
            "start_date": "2026-06-01",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    rid = created.json()["id"]

    run = api_client.post(
        f"/api/recurring-rules/{rid}/run", headers=auth_headers
    )
    assert run.status_code == 200
    assert run.json()["generated"] >= 1

    listed = api_client.get("/api/recurring-rules", headers=auth_headers).json()
    assert listed[0]["last_generated_date"] is not None


def test_cron_endpoint_requires_secret(api_client: TestClient) -> None:
    assert api_client.post("/api/cron/generate-recurring").status_code == 401
    ok = api_client.post(
        "/api/cron/generate-recurring",
        headers={"X-Cron-Secret": "test-cron-secret"},
    )
    assert ok.status_code == 200


def test_rule_create_blocked_in_demo(
    api_client: TestClient, auth_headers, account: Account, demo_mode
) -> None:
    resp = api_client.post(
        "/api/recurring-rules",
        json={
            "name": "X",
            "account_id": account.id,
            "amount": "1.00",
            "currency": "USD",
            "frequency": "monthly",
            "start_date": "2026-06-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 403
