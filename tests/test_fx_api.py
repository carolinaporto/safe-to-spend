import datetime as dt
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.fx_rate import FxRate
from backend.services import fx_provider


def test_fx_rate_endpoint_requires_auth(api_client: TestClient) -> None:
    assert api_client.get("/api/fx/rate?base=BRL").status_code == 403


def test_fx_rate_endpoint_returns_stored_rate_as_string(
    api_client: TestClient, auth_headers: dict, db: Session
) -> None:
    db.add(
        FxRate(
            date=dt.date(2025, 9, 1),
            base="BRL",
            quote="USD",
            rate=Decimal("0.18500000"),
            source="test",
        )
    )
    db.flush()

    resp = api_client.get(
        "/api/fx/rate?date=2025-09-05&base=BRL&quote=USD", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["rate"] == "0.18500000"


def test_fx_rate_endpoint_404_when_no_rate(
    api_client: TestClient, auth_headers: dict
) -> None:
    resp = api_client.get("/api/fx/rate?base=BRL", headers=auth_headers)
    assert resp.status_code == 404


def test_cron_fetch_fx_rejects_bad_secret(api_client: TestClient) -> None:
    assert api_client.post("/api/cron/fetch-fx").status_code == 401
    assert (
        api_client.post(
            "/api/cron/fetch-fx", headers={"X-Cron-Secret": "wrong"}
        ).status_code
        == 401
    )


def test_cron_fetch_fx_stores_both_directions(
    api_client: TestClient, db: Session, monkeypatch
) -> None:
    monkeypatch.setattr(
        fx_provider,
        "fetch_usd_brl",
        lambda *a, **k: {
            ("USD", "BRL"): Decimal("5.00000000"),
            ("BRL", "USD"): Decimal("0.20000000"),
        },
    )
    from backend.config import get_settings

    resp = api_client.post(
        "/api/cron/fetch-fx",
        headers={"X-Cron-Secret": get_settings().cron_secret},
    )
    assert resp.status_code == 200

    today = dt.date.today()
    assert db.get(FxRate, (today, "USD", "BRL")).rate == Decimal("5.00000000")
    assert db.get(FxRate, (today, "BRL", "USD")).rate == Decimal("0.20000000")
