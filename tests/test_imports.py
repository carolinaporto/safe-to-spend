import datetime as dt
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.importers import detect_parser, parse_csv
from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import (
    AccountKind,
    CategoryNature,
    Currency,
    MerchantMatchType,
)
from backend.models.fx_rate import FxRate
from backend.models.merchant_rule import MerchantRule
from backend.models.transaction import Transaction

CHASE_CSV = (
    b"Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n"
    b"09/01/2026,09/02/2026,TRADER JOE'S #201,Groceries,Sale,-42.17,\n"
    b"09/02/2026,09/03/2026,BLUE BOTTLE,Food,Sale,-6.50,\n"
    b"09/03/2026,09/04/2026,PAYROLL DEPOSIT,,Credit,1500.00,\n"
)

AMEX_CSV = (
    b"Date,Description,Card Member,Account #,Amount\n"
    b"09/01/2026,UNIQLO USA,JANE DOE,-12345,84.20\n"
    b"09/05/2026,AUTOPAY PAYMENT,JANE DOE,-12345,-84.20\n"
)

WISE_CSV = (
    b"TransferWise ID,Date,Amount,Currency,Description,Merchant\n"
    b"TW-1,2026-09-01,-35.00,USD,Card transaction,H MART\n"
    b"TW-2,2026-09-02,-120.00,BRL,Card transaction,PADARIA BRASIL\n"
)


@pytest.fixture
def chase(db: Session) -> Account:
    a = Account(
        name="Chase",
        institution="Chase",
        kind=AccountKind.checking,
        currency=Currency.USD,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2026, 1, 1),
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def wise_brl(db: Session) -> Account:
    a = Account(
        name="Wise BRL",
        institution="Wise",
        kind=AccountKind.checking,
        currency=Currency.BRL,
        opening_balance=Decimal("0.00"),
        opening_date=dt.date(2026, 1, 1),
    )
    db.add(a)
    db.flush()
    return a


# --------------------------------------------------------------- parsers

def test_detect_parser_picks_the_right_one() -> None:
    assert detect_parser(["Transaction Date", "Post Date", "Description", "Amount"]) == "chase"
    assert detect_parser(["Date", "Description", "Card Member", "Amount"]) == "amex"
    assert detect_parser(["TransferWise ID", "Date", "Amount", "Currency"]) == "wise"
    assert detect_parser(["when", "how much", "note"]) == "generic"


def test_chase_signs_and_directions() -> None:
    parser, rows = parse_csv(CHASE_CSV, "USD")
    assert parser == "chase"
    assert [r.direction.value for r in rows] == ["out", "out", "in"]
    assert rows[0].amount == Decimal("42.17")
    assert rows[2].amount == Decimal("1500.00")


def test_amex_charge_is_positive_payment_is_negative() -> None:
    _, rows = parse_csv(AMEX_CSV, "USD")
    assert rows[0].direction.value == "out"  # a charge
    assert rows[1].direction.value == "in"  # a payment
    assert rows[0].merchant_raw == "UNIQLO USA"


def test_wise_reads_currency_per_row() -> None:
    _, rows = parse_csv(WISE_CSV, "BRL")
    assert rows[0].currency == "USD"
    assert rows[1].currency == "BRL"
    assert rows[0].external_id == "TW-1"


# --------------------------------------------------------------- preview

def _upload(client, url, account, csv, **extra):
    return client.post(
        url,
        data={"account_id": account.id, **extra},
        files={"file": ("statement.csv", csv, "text/csv")},
    )


def test_preview_classifies_rows_and_applies_rules(
    api_client: TestClient, auth_headers: dict, chase: Account, db: Session
) -> None:
    groceries = Category(name="Groceries", nature=CategoryNature.essential)
    db.add(groceries)
    db.flush()
    db.add(
        MerchantRule(
            pattern="TRADER JOE",
            match_type=MerchantMatchType.contains,
            category_id=groceries.id,
            merchant_clean="Trader Joe's",
        )
    )
    db.flush()

    api_client.headers.update(auth_headers)
    body = _upload(api_client, "/api/imports/preview", chase, CHASE_CSV).json()
    assert body["parser"] == "chase"
    assert body["summary"] == {
        "total": 3,
        "new": 1,
        "duplicate": 0,
        "uncategorized": 2,
    }
    tj = body["rows"][0]
    assert tj["category_name"] == "Groceries"
    assert tj["merchant_clean"] == "Trader Joe's"
    assert tj["status"] == "new"


def test_preview_does_not_write(
    api_client: TestClient, auth_headers: dict, chase: Account, db: Session
) -> None:
    api_client.headers.update(auth_headers)
    _upload(api_client, "/api/imports/preview", chase, CHASE_CSV)
    assert db.query(Transaction).count() == 0


# ---------------------------------------------------------------- commit

def test_commit_imports_then_reimport_inserts_nothing(
    api_client: TestClient, auth_headers: dict, chase: Account
) -> None:
    api_client.headers.update(auth_headers)
    first = _upload(api_client, "/api/imports/commit", chase, CHASE_CSV).json()
    assert first["imported_count"] == 3
    assert first["duplicate_count"] == 0

    again = _upload(api_client, "/api/imports/commit", chase, CHASE_CSV).json()
    assert again["imported_count"] == 0
    assert again["duplicate_count"] == 3


def test_commit_honours_overrides_and_skip(
    api_client: TestClient, auth_headers: dict, chase: Account, db: Session
) -> None:
    coffee = Category(name="Coffee", nature=CategoryNature.discretionary)
    db.add(coffee)
    db.flush()
    api_client.headers.update(auth_headers)

    preview = _upload(
        api_client, "/api/imports/preview", chase, CHASE_CSV
    ).json()
    keys = {r["merchant_raw"]: r["key"] for r in preview["rows"]}

    import json

    committed = _upload(
        api_client,
        "/api/imports/commit",
        chase,
        CHASE_CSV,
        overrides=json.dumps({keys["BLUE BOTTLE"]: coffee.id}),
        skip=json.dumps([keys["PAYROLL DEPOSIT"]]),
    ).json()
    assert committed["imported_count"] == 2

    rows = db.query(Transaction).all()
    blue = next(t for t in rows if t.merchant_raw == "BLUE BOTTLE")
    assert blue.category_id == coffee.id
    assert blue.needs_review is False


def test_commit_blocked_in_demo(
    api_client: TestClient, auth_headers: dict, chase: Account, demo_mode
) -> None:
    api_client.headers.update(auth_headers)
    resp = _upload(api_client, "/api/imports/commit", chase, CHASE_CSV)
    assert resp.status_code == 403


def test_wise_import_converts_per_row_currency(
    api_client: TestClient,
    auth_headers: dict,
    wise_brl: Account,
    db: Session,
) -> None:
    db.add(
        FxRate(
            date=dt.date(2026, 9, 2),
            base="BRL",
            quote="USD",
            rate=Decimal("0.19000000"),
            source="test",
        )
    )
    db.flush()
    api_client.headers.update(auth_headers)
    _upload(api_client, "/api/imports/commit", wise_brl, WISE_CSV)

    brl_txn = db.query(Transaction).filter_by(currency="BRL").one()
    assert brl_txn.amount_usd == Decimal("22.80")  # 120 * 0.19


# ---------------------------------------------------------- review queue

def test_review_queue_lists_needs_review(
    api_client: TestClient, auth_headers: dict, chase: Account
) -> None:
    api_client.headers.update(auth_headers)
    _upload(api_client, "/api/imports/commit", chase, CHASE_CSV)
    body = api_client.get("/api/imports/review-queue").json()
    # every row was uncategorized -> all flagged
    assert body["total"] == 3
    assert all(item["source"] == "csv" for item in body["items"])
