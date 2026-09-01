"""American Express CSV.

Columns vary, but always: Date, Description, Amount (plus optional Card
Member / Account # / Extended Details / "Appears On Your Statement As").

Amex's sign convention is the opposite of a bank: a **charge is positive**
and a payment/credit is negative.
"""

from backend.importers.base import (
    ParsedRow,
    parse_amount,
    parse_date,
    signed_to_row,
)

name = "amex"


def sniff(header: list[str]) -> bool:
    cols = {h.lower() for h in header}
    has_core = {"date", "amount"} <= cols and any(
        "description" in c for c in cols
    )
    amex_marker = any(
        c in cols
        for c in (
            "card member",
            "appears on your statement as",
            "extended details",
        )
    )
    return has_core and amex_marker


def parse(rows: list[dict[str, str]], currency: str) -> list[ParsedRow]:
    def col(row: dict[str, str], *names: str) -> str:
        lower = {k.lower(): v for k, v in row.items()}
        for n in names:
            if lower.get(n):
                return lower[n]
        return ""

    out: list[ParsedRow] = []
    for row in rows:
        amount_raw = col(row, "amount")
        date_raw = col(row, "date")
        if not amount_raw.strip() or not date_raw.strip():
            continue
        merchant = col(
            row, "appears on your statement as", "description"
        )
        # Flip: on Amex a positive amount is a charge (money out).
        out.append(
            signed_to_row(
                date=parse_date(date_raw),
                signed_amount=parse_amount(amount_raw),
                currency=currency,
                merchant_raw=merchant,
                outflow_is_negative=False,
                description=col(row, "extended details", "description"),
            )
        )
    return out
