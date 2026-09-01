import datetime as dt
from decimal import Decimal

import pytest
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
from backend.models.fx_rate import FxRate
from backend.models.transaction import Transaction
from backend.services.income import income_summary
from backend.services.transfers import TransferInput, create_transfer

TODAY = dt.date.today()


@pytest.fixture
def setup(db: Session):
    wb = Account(
        name="Wise BRL",
        institution="Wise",
        kind=AccountKind.checking,
        currency=Currency.BRL,
        opening_balance=Decimal("100000.00"),
        opening_date=dt.date(2026, 1, 1),
    )
    ch = Account(
        name="Chase",
        institution="Chase",
        kind=AccountKind.checking,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2026, 1, 1),
    )
    db.add_all([wb, ch])
    funding = Category(name="Funding", nature=CategoryNature.income)
    db.add(funding)
    db.add(
        FxRate(
            date=TODAY, base="BRL", quote="USD", rate=Decimal("0.185"), source="t"
        )
    )
    db.flush()
    return wb, ch, funding


def test_income_summary_tracks_conversion_and_cumulative_fx_cost(
    db: Session, setup
) -> None:
    wb, ch, funding = setup
    db.add(
        Transaction(
            date=TODAY,
            account_id=wb.id,
            direction=TransactionDirection.in_,
            kind=TransactionKind.income,
            amount=Decimal("100000.00"),
            currency="BRL",
            fx_rate_to_usd=Decimal("0.185"),
            amount_usd=Decimal("18500.00"),
            category_id=funding.id,
        )
    )
    db.flush()

    create_transfer(
        db,
        TransferInput(
            date=TODAY,
            from_account_id=wb.id,
            to_account_id=ch.id,
            amount_out=Decimal("5000.00"),
            amount_in=Decimal("890.00"),
            market_rate=Decimal("0.185"),
        ),
    )

    s = income_summary(db)
    assert s["total_funding_brl"] == Decimal("100000.00")
    assert s["converted_brl"] == Decimal("5000.00")
    assert s["converted_usd"] == Decimal("890.00")
    assert s["cumulative_fx_cost_usd"] == Decimal("35.00")  # 5000*.185 − 890
    # 100000 opening + 100000 income − 5000 transferred out
    assert s["still_in_brl"] == Decimal("195000.00")
    assert len(s["entries"]) == 1


def test_income_endpoint(api_client, auth_headers, setup) -> None:
    resp = api_client.get("/api/income/summary", headers=auth_headers)
    assert resp.status_code == 200
    assert "cumulative_fx_cost_usd" in resp.json()
