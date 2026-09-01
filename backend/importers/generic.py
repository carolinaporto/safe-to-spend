"""Fallback parser for any CSV with recognisable date / amount / description
columns. Matches column names case-insensitively and by common aliases.
"""

from backend.importers.base import (
    ParsedRow,
    parse_amount,
    parse_date,
    signed_to_row,
)

name = "generic"

_DATE = ("date", "transaction date", "posted date", "posting date", "time")
_AMOUNT = ("amount", "value", "debit/credit", "amount (usd)")
_MERCHANT = ("description", "merchant", "name", "details", "memo", "narrative")
_CURRENCY = ("currency", "ccy", "currency code")
_ID = ("id", "transaction id", "reference", "ref")


def _pick(header: list[str], aliases: tuple[str, ...]) -> str | None:
    lower = {h.lower().strip(): h for h in header}
    for alias in aliases:
        if alias in lower:
            return lower[alias]
    return None


def sniff(header: list[str]) -> bool:
    return bool(_pick(header, _DATE) and _pick(header, _AMOUNT))


def parse(
    rows: list[dict[str, str]], currency: str, header: list[str] | None = None
) -> list[ParsedRow]:
    header = header or list(rows[0].keys()) if rows else []
    date_col = _pick(header, _DATE)
    amount_col = _pick(header, _AMOUNT)
    merchant_col = _pick(header, _MERCHANT)
    currency_col = _pick(header, _CURRENCY)
    id_col = _pick(header, _ID)
    if not date_col or not amount_col:
        return []

    out: list[ParsedRow] = []
    for row in rows:
        if not row.get(amount_col, "").strip() or not row.get(date_col, "").strip():
            continue
        out.append(
            signed_to_row(
                date=parse_date(row[date_col]),
                signed_amount=parse_amount(row[amount_col]),
                currency=(
                    (row.get(currency_col) or currency).strip().upper()
                    if currency_col
                    else currency
                ),
                merchant_raw=row.get(merchant_col, "") if merchant_col else "",
                external_id=row.get(id_col) if id_col else None,
            )
        )
    return out
