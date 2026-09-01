"""Per-institution CSV parsers mapping to one shared row shape (spec 5)."""

import csv
import datetime as dt
import hashlib
import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from backend.models.enums import TransactionDirection
from backend.money import money


@dataclass
class ParsedRow:
    date: dt.date
    amount: Decimal  # always positive, in ``currency``
    direction: TransactionDirection
    currency: str
    merchant_raw: str
    description: str = ""
    external_id: str | None = None
    tags: list[str] = field(default_factory=list)

    def dedupe_key(self) -> str:
        """Hash of (date, amount, merchant, currency) — the spec's dedupe tuple
        minus account_id (callers scope by account). Also the stable id used to
        carry preview edits into the commit."""
        return content_key(
            self.date, self.amount, self.merchant_raw, self.currency
        )


def content_key(
    date: dt.date, amount: Decimal, merchant_raw: str, currency: str
) -> str:
    parts = (
        date.isoformat(),
        format(amount, "f"),
        (merchant_raw or "").strip().upper(),
        currency.upper(),
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


class ParseError(ValueError):
    pass


# ---------------------------------------------------------------- helpers

def parse_amount(raw: str) -> Decimal:
    cleaned = raw.strip().replace(",", "").replace("$", "").replace("R$", "")
    if cleaned in ("", "-", "--"):
        raise ParseError(f"empty amount: {raw!r}")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ParseError(f"bad amount: {raw!r}") from exc


_DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d/%m/%Y", "%d-%m-%Y")


def parse_date(raw: str) -> dt.date:
    value = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    # ISO with time
    try:
        return dt.datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise ParseError(f"bad date: {raw!r}") from exc


def signed_to_row(
    *,
    date: dt.date,
    signed_amount: Decimal,
    currency: str,
    merchant_raw: str,
    outflow_is_negative: bool = True,
    description: str = "",
    external_id: str | None = None,
) -> ParsedRow:
    """Build a ParsedRow from a signed amount, normalising to positive."""
    is_out = (signed_amount < 0) == outflow_is_negative
    return ParsedRow(
        date=date,
        amount=money(abs(signed_amount)),
        direction=TransactionDirection.out if is_out else TransactionDirection.in_,
        currency=currency,
        merchant_raw=merchant_raw.strip(),
        description=description.strip(),
        external_id=external_id or None,
    )


def read_rows(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise ParseError("empty file")
    header = [h.strip() for h in rows[0]]
    dicts = [
        {header[i]: (r[i] if i < len(r) else "") for i in range(len(header))}
        for r in rows[1:]
    ]
    return header, dicts
