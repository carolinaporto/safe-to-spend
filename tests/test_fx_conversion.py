import datetime as dt
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.models.fx_rate import FxRate
from backend.services.fx import Conversion, convert_to_usd, get_rate


def _rate(db: Session, date: str, base: str, quote: str, value: str) -> None:
    db.add(
        FxRate(
            date=dt.date.fromisoformat(date),
            base=base,
            quote=quote,
            rate=Decimal(value),
            source="test",
        )
    )
    db.flush()


def test_usd_amount_passes_through_unchanged(db: Session) -> None:
    result = convert_to_usd(db, Decimal("42.42"), "USD", dt.date(2025, 9, 1))
    assert result == Conversion(Decimal("1"), Decimal("42.42"), stale=False)


def test_brl_converts_at_the_rate_for_that_date(db: Session) -> None:
    _rate(db, "2025-09-01", "BRL", "USD", "0.18500000")
    result = convert_to_usd(db, Decimal("100.00"), "BRL", dt.date(2025, 9, 1))
    assert result.rate == Decimal("0.18500000")
    assert result.amount_usd == Decimal("18.50")
    assert result.stale is False


def test_conversion_rounds_half_up(db: Session) -> None:
    _rate(db, "2025-09-01", "BRL", "USD", "0.18333333")
    # 55.55 * 0.18333333 = 10.18416... -> 10.18
    result = convert_to_usd(db, Decimal("55.55"), "BRL", dt.date(2025, 9, 1))
    assert result.amount_usd == Decimal("10.18")


def test_falls_back_to_most_recent_prior_rate_and_flags_stale(
    db: Session,
) -> None:
    _rate(db, "2025-08-28", "BRL", "USD", "0.20000000")
    result = convert_to_usd(db, Decimal("10.00"), "BRL", dt.date(2025, 9, 1))
    assert result.rate == Decimal("0.20000000")
    assert result.amount_usd == Decimal("2.00")
    assert result.stale is True


def test_uses_inverse_rate_when_only_the_other_direction_is_stored(
    db: Session,
) -> None:
    _rate(db, "2025-09-01", "USD", "BRL", "5.00000000")
    assert get_rate(db, dt.date(2025, 9, 1), "BRL", "USD") == Decimal(
        "0.20000000"
    )


def test_missing_rate_records_at_parity_and_flags_stale(db: Session) -> None:
    result = convert_to_usd(db, Decimal("10.00"), "BRL", dt.date(2025, 9, 1))
    assert result.rate == Decimal("1")
    assert result.amount_usd == Decimal("10.00")
    assert result.stale is True
