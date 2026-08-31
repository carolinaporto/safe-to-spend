from decimal import Decimal

import pytest

from backend.money import money, rate, to_decimal
from backend.schemas.common import ApiModel, MoneyStr, RateStr


def test_money_rounds_half_up_to_two_places() -> None:
    assert money("2.005") == Decimal("2.01")
    assert money("2.014") == Decimal("2.01")
    assert money("2.015") == Decimal("2.02")
    assert money("-2.005") == Decimal("-2.01")


def test_rate_rounds_half_up_to_eight_places() -> None:
    assert rate("0.123456785") == Decimal("0.12345679")
    assert rate("5") == Decimal("5.00000000")


def test_to_decimal_refuses_float() -> None:
    with pytest.raises(TypeError):
        to_decimal(1.1)


def test_money_field_accepts_string_or_int_and_serializes_to_string() -> None:
    class M(ApiModel):
        amount: MoneyStr
        fx: RateStr

    parsed = M(amount="10.1", fx="0.185")
    assert parsed.amount == Decimal("10.10")
    dumped = parsed.model_dump(mode="json")
    assert dumped == {"amount": "10.10", "fx": "0.18500000"}
    assert isinstance(dumped["amount"], str)
