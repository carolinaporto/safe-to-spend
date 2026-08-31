"""Decimal helpers for money and FX rates.

Spec invariants: money is 2 dp, rates are 8 dp, rounding is ROUND_HALF_UP,
and no ``float`` ever touches a monetary value.
"""

from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")
RATE_QUANT = Decimal("0.00000001")
ZERO = Decimal("0.00")
ONE = Decimal("1")


def to_decimal(value: object) -> Decimal:
    """Build a Decimal without ever going through float."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise TypeError("refusing to build a monetary Decimal from a float")
    return Decimal(str(value))


def money(value: object) -> Decimal:
    """Quantize to 2 decimal places, ROUND_HALF_UP."""
    return to_decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def rate(value: object) -> Decimal:
    """Quantize to 8 decimal places, ROUND_HALF_UP."""
    return to_decimal(value).quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def money_str(value: Decimal) -> str:
    """Plain decimal string, no scientific notation (for JSON responses)."""
    return format(money(value), "f")
