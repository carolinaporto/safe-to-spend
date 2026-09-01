"""CSV import: preview (no writes) and commit (spec section 5)."""

import datetime as dt
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.importers import ParsedRow, parse_csv
from backend.importers.base import content_key
from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import (
    TransactionDirection,
    TransactionKind,
    TransactionSource,
)
from backend.models.import_batch import ImportBatch
from backend.models.transaction import Transaction
from backend.services.fx import convert_to_usd
from backend.services.merchant_rules import (
    bump_hit_counts,
    load_rules,
    match_merchant,
)

NEW = "new"
DUPLICATE = "duplicate"
UNCATEGORIZED = "uncategorized"


@dataclass
class PreviewRow:
    key: str
    date: dt.date
    amount: Decimal
    direction: str
    currency: str
    merchant_raw: str
    merchant_clean: str | None
    category_id: int | None
    category_name: str | None
    amount_usd: Decimal
    fx_stale: bool
    status: str
    external_id: str | None = None
    rule_id: int | None = None


@dataclass
class Preview:
    parser: str
    account_id: int
    filename: str
    rows: list[PreviewRow] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        counts = Counter(r.status for r in self.rows)
        return {
            "total": len(self.rows),
            "new": counts[NEW],
            "duplicate": counts[DUPLICATE],
            "uncategorized": counts[UNCATEGORIZED],
        }


def _existing_keys(
    db: Session, account_id: int, parsed: list[ParsedRow]
) -> tuple[set[str], set[str]]:
    """(content keys, external ids) already stored for this account, scoped to
    the date range of the file."""
    if not parsed:
        return set(), set()
    lo = min(r.date for r in parsed)
    hi = max(r.date for r in parsed)
    rows = db.execute(
        select(
            Transaction.date,
            Transaction.amount,
            Transaction.merchant_raw,
            Transaction.currency,
            Transaction.external_id,
        ).where(
            Transaction.account_id == account_id,
            Transaction.date >= lo,
            Transaction.date <= hi,
        )
    ).all()
    keys = {
        content_key(d, amount, merchant or "", currency)
        for d, amount, merchant, currency in (
            (r.date, r.amount, r.merchant_raw, r.currency) for r in rows
        )
    }
    externals = {r.external_id for r in rows if r.external_id}
    return keys, externals


def build_preview(
    db: Session,
    account: Account,
    filename: str,
    content: bytes,
    parser_name: str | None,
) -> Preview:
    parser, parsed = parse_csv(content, account.currency.value, parser_name)
    rules = load_rules(db)
    categories = {
        c.id: c.name for c in db.execute(select(Category)).scalars()
    }
    existing_keys, existing_externals = _existing_keys(db, account.id, parsed)

    preview = Preview(parser=parser, account_id=account.id, filename=filename)
    seen_in_file: set[str] = set()

    for row in parsed:
        key = row.dedupe_key()
        is_dup = (
            key in existing_keys
            or key in seen_in_file
            or (row.external_id is not None and row.external_id in existing_externals)
        )
        seen_in_file.add(key)

        rule = match_merchant(rules, row.merchant_raw)
        category_id = rule.category_id if rule else None
        merchant_clean = rule.merchant_clean if rule else None

        conversion = convert_to_usd(db, row.amount, row.currency, row.date)
        fx_stale = row.currency != "USD" and conversion.stale

        if is_dup:
            status = DUPLICATE
        elif category_id is None:
            status = UNCATEGORIZED
        else:
            status = NEW

        preview.rows.append(
            PreviewRow(
                key=key,
                date=row.date,
                amount=row.amount,
                direction=row.direction.value,
                currency=row.currency,
                merchant_raw=row.merchant_raw,
                merchant_clean=merchant_clean,
                category_id=category_id,
                category_name=categories.get(category_id),
                amount_usd=conversion.amount_usd,
                fx_stale=fx_stale,
                status=status,
                external_id=row.external_id,
                rule_id=rule.rule_id if rule else None,
            )
        )
    return preview


_KIND_BY_DIRECTION = {
    TransactionDirection.out: TransactionKind.expense,
    TransactionDirection.in_: TransactionKind.income,
}


def commit_import(
    db: Session,
    account: Account,
    filename: str,
    content: bytes,
    parser_name: str | None,
    *,
    overrides: dict[str, int | None] | None = None,
    skip: set[str] | None = None,
) -> ImportBatch:
    overrides = overrides or {}
    skip = skip or set()
    preview = build_preview(db, account, filename, content, parser_name)

    batch = ImportBatch(
        account_id=account.id,
        filename=filename,
        parser=preview.parser,
        row_count=len(preview.rows),
    )
    db.add(batch)
    db.flush()

    imported = 0
    duplicates = 0
    rule_hits: Counter[int] = Counter()

    for row in preview.rows:
        if row.status == DUPLICATE:
            duplicates += 1
            continue
        if row.key in skip:
            continue

        category_id = overrides.get(row.key, row.category_id)
        needs_review = row.fx_stale or category_id is None
        direction = TransactionDirection(row.direction)
        db.add(
            Transaction(
                date=row.date,
                account_id=account.id,
                direction=direction,
                kind=_KIND_BY_DIRECTION[direction],
                amount=row.amount,
                currency=row.currency,
                fx_rate_to_usd=convert_to_usd(
                    db, row.amount, row.currency, row.date
                ).rate,
                amount_usd=row.amount_usd,
                category_id=category_id,
                merchant_raw=row.merchant_raw,
                merchant_clean=row.merchant_clean,
                source=TransactionSource.csv,
                external_id=row.external_id,
                import_batch_id=batch.id,
                needs_review=needs_review,
            )
        )
        imported += 1
        if row.rule_id is not None:
            rule_hits[row.rule_id] += 1

    batch.imported_count = imported
    batch.duplicate_count = duplicates
    bump_hit_counts(db, rule_hits)
    db.commit()
    db.refresh(batch)
    return batch
