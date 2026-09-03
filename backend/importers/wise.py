"""Wise (TransferWise) CSV — two different exports are supported.

1. **Balance statement** ("Download statement" from a balance):
       TransferWise ID, Date, Amount, Currency, Description, Merchant, ...
   ``Amount`` is signed and in one currency per row.

2. **Transaction / activity export** ("Transactions" -> Export):
       ID, Status, Direction, Created on, Finished on,
       Source fee amount, Source fee currency, Target fee amount,
       Target fee currency, Source name, Source amount (after fees),
       Source currency, Target name, Target amount (after fees),
       Target currency, Exchange rate, Reference, Batch, Created by,
       Category, Note
   Each row has a *source* side and a *target* side. When importing into one
   account we take whichever side is in the account's currency:
     - source side  -> money left the account  (amount + source fee)
     - target side  -> money entered the account (amount after fees)
   Rows that touch neither the source nor the target in the account currency
   are skipped, as are cancelled / refunded / bounced transfers.
"""

from decimal import Decimal

from backend.importers.base import (
    ParsedRow,
    ParseError,
    parse_amount,
    parse_date,
    signed_to_row,
)
from backend.models.enums import TransactionDirection
from backend.money import money

name = "wise"

_ACTIVITY_MARKERS = {"Source amount (after fees)", "Target amount (after fees)"}
_SKIP_STATUSES = {
    "CANCELLED",
    "REFUNDED",
    "FUNDS_REFUNDED",
    "BOUNCED_BACK",
    "CHARGED_BACK",
    "PROCESSING",
}


def sniff(header: list[str]) -> bool:
    cols = set(header)
    statement = bool({"TransferWise ID", "ID", "Wise ID"} & cols) and {
        "Amount",
        "Currency",
        "Date",
    } <= cols
    activity = "Direction" in cols and _ACTIVITY_MARKERS & cols
    return statement or bool(activity)


def _get(row: dict[str, str], *names: str) -> str:
    for n in names:
        if row.get(n):
            return row[n]
    return ""


def _safe_amount(raw: str) -> Decimal:
    try:
        return parse_amount(raw)
    except ParseError:
        return Decimal("0")


def _parse_statement(rows: list[dict[str, str]], currency: str) -> list[ParsedRow]:
    out: list[ParsedRow] = []
    for row in rows:
        amount_raw = _get(row, "Amount")
        if not amount_raw.strip():
            continue
        row_currency = (_get(row, "Currency") or currency).strip().upper()
        out.append(
            signed_to_row(
                date=parse_date(_get(row, "Date", "Finished on", "Created on")),
                signed_amount=parse_amount(amount_raw),
                currency=row_currency,
                merchant_raw=_get(row, "Merchant", "Payee Name", "Description"),
                description=_get(row, "Description", "Payment Reference"),
                external_id=_get(row, "TransferWise ID", "ID", "Wise ID") or None,
            )
        )
    return out


def _outflow(row: dict[str, str], acct: str) -> Decimal:
    """What left the account's balance on the source side (amount + fee)."""
    gross = _safe_amount(_get(row, "Source amount (after fees)"))
    if _get(row, "Source fee currency").strip().upper() == acct:
        gross += _safe_amount(_get(row, "Source fee amount"))
    return gross


def _parse_activity(rows: list[dict[str, str]], currency: str) -> list[ParsedRow]:
    acct = currency.strip().upper()
    out: list[ParsedRow] = []
    for row in rows:
        if _get(row, "Status").strip().upper() in _SKIP_STATUSES:
            continue

        direction = _get(row, "Direction").strip().upper()
        src_ccy = _get(row, "Source currency").strip().upper()
        tgt_ccy = _get(row, "Target currency").strip().upper()
        when = parse_date(_get(row, "Finished on", "Created on"))
        ext_id = _get(row, "ID") or None
        note = _get(row, "Note", "Reference").strip()

        # Which side of the transfer is this account? OUT -> source, IN ->
        # target, anything else (conversion between own balances) -> whichever
        # side carries the account currency.
        if direction == "OUT" or (direction not in ("IN",) and src_ccy == acct):
            if src_ccy != acct:
                continue
            gross = _outflow(row, acct)
            leg = TransactionDirection.out
            merchant = _get(row, "Target name", "Reference", "Note")
        elif direction == "IN" or tgt_ccy == acct:
            if tgt_ccy != acct:
                continue
            gross = _safe_amount(_get(row, "Target amount (after fees)"))
            leg = TransactionDirection.in_
            merchant = _get(row, "Source name", "Reference", "Note")
        else:
            continue  # doesn't touch the account currency

        if gross <= 0:
            continue
        out.append(
            ParsedRow(
                date=when,
                amount=money(gross),
                direction=leg,
                currency=acct,
                merchant_raw=merchant.strip(),
                description=note,
                external_id=ext_id,
            )
        )
    return out


def parse(rows: list[dict[str, str]], currency: str) -> list[ParsedRow]:
    if rows and _ACTIVITY_MARKERS & set(rows[0]):
        return _parse_activity(rows, currency)
    return _parse_statement(rows, currency)
