"""Chase CSV — both the checking export and the credit-card export.

Checking:    Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #
Credit card: Transaction Date, Post Date, Description, Category, Type, Amount, Memo

In both, ``Amount`` is negative for money leaving the account / a purchase.
"""

from backend.importers.base import (
    ParsedRow,
    parse_amount,
    parse_date,
    signed_to_row,
)

name = "chase"

_CHECKING = {"Posting Date", "Description", "Amount"}
_CREDIT = {"Transaction Date", "Description", "Amount"}


def sniff(header: list[str]) -> bool:
    cols = set(header)
    if "Details" in cols and _CHECKING <= cols:
        return True
    return "Transaction Date" in cols and "Post Date" in cols and "Amount" in cols


def parse(rows: list[dict[str, str]], currency: str) -> list[ParsedRow]:
    out: list[ParsedRow] = []
    for row in rows:
        date_raw = row.get("Transaction Date") or row.get("Posting Date")
        if not date_raw or not row.get("Amount", "").strip():
            continue
        out.append(
            signed_to_row(
                date=parse_date(date_raw),
                signed_amount=parse_amount(row["Amount"]),
                currency=currency,
                merchant_raw=row.get("Description", ""),
                description=row.get("Memo", "") or row.get("Type", ""),
            )
        )
    return out
