import datetime as dt
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.account import Account
from backend.models.enums import AccountKind, Currency


def _account(db: Session) -> None:
    db.add(
        Account(
            name="Wise USD",
            institution="Wise",
            kind=AccountKind.checking,
            currency=Currency.USD,
            opening_balance=Decimal("123.45"),
            opening_date=dt.date(2025, 8, 1),
        )
    )
    db.flush()


def test_backup_download_requires_auth(api_client: TestClient) -> None:
    assert api_client.get("/api/backup").status_code == 403


def test_backup_download_returns_json_snapshot(
    api_client: TestClient, auth_headers: dict, db: Session
) -> None:
    _account(db)
    resp = api_client.get("/api/backup", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert body["counts"]["accounts"] == 1
    assert body["tables"]["accounts"][0]["opening_balance"] == "123.45"


def test_cron_backup_requires_secret(api_client: TestClient) -> None:
    assert api_client.post("/api/cron/backup").status_code == 401


def test_cron_backup_returns_snapshot(
    api_client: TestClient, db: Session
) -> None:
    _account(db)
    resp = api_client.post(
        "/api/cron/backup",
        headers={"X-Cron-Secret": get_settings().cron_secret},
    )
    assert resp.status_code == 200
    assert resp.json()["counts"]["accounts"] == 1
