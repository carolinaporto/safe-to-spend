"""Wise (TransferWise) balance-statement CSV.

Header (multi-currency — one file can mix USD and BRL rows):
    TransferWise ID, Date, Amount, Currency, Description, Payment Reference,
    Running Balance, Exchange From, Exchange To, Exchange Rate, Payer Name,
    Payee Name, Payee Account Number, Merchant, ...

``Amount`` is signed (negative = money out). ``Currency`` is per row, so the
account currency is ignored here.
"""

from backend.importers.base import (
    ParsedRow,
    parse_amount,
    parse_date,
    signed_to_row,
)

name = "wise"


def sniff(header: list[str]) -> bool:
    cols = set(header)
    id_col = {"TransferWise ID", "ID", "Wise ID"} & cols
    return bool(id_col) and {"Amount", "Currency", "Date"} <= cols


def parse(rows: list[dict[str, str]], currency: str) -> list[ParsedRow]:
    def get(row: dict[str, str], *names: str) -> str:
        for n in names:
            if row.get(n):
                return row[n]
        return ""

    out: list[ParsedRow] = []
    for row in rows:
        amount_raw = get(row, "Amount")
        if not amount_raw.strip():
            continue
        row_currency = (get(row, "Currency") or currency).strip().upper()
        merchant = get(row, "Merchant", "Payee Name", "Description")
        out.append(
            signed_to_row(
                date=parse_date(get(row, "Date", "Finished on", "Created on")),
                signed_amount=parse_amount(amount_raw),
                currency=row_currency,
                merchant_raw=merchant,
                description=get(row, "Description", "Payment Reference"),
                external_id=get(row, "TransferWise ID", "ID", "Wise ID") or None,
            )
        )
    return out
