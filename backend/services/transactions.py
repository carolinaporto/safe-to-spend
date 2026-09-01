"""Manual transaction creation and editing.

Currency conversion happens here, at write time, and is persisted on the row
(spec invariant 3). Direction follows the kind unless given explicitly.
"""

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import TransactionDirection, TransactionKind
from backend.models.transaction import Transaction
from backend.schemas.transaction import (
    MANUAL_KINDS,
    TransactionCreate,
    TransactionUpdate,
)
from backend.services.fx import convert_to_usd

_DIRECTION_BY_KIND = {
    TransactionKind.expense: TransactionDirection.out,
    TransactionKind.income: TransactionDirection.in_,
}


def _require_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown account_id")
    return account


def _check_category(db: Session, category_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown category_id"
        )


def _resolve_direction(
    kind: TransactionKind, given: TransactionDirection | None
) -> TransactionDirection:
    if kind in _DIRECTION_BY_KIND:
        return _DIRECTION_BY_KIND[kind]
    if given is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{kind.value} transactions require an explicit direction",
        )
    return given


def _apply_conversion(
    db: Session, txn: Transaction, currency: str, on_date: dt.date
) -> None:
    conversion = convert_to_usd(db, txn.amount, currency, on_date)
    txn.currency = currency
    txn.fx_rate_to_usd = conversion.rate
    txn.amount_usd = conversion.amount_usd
    # Reflects the current rate situation: a re-priced row with a real rate now
    # clears its own review flag; a still-stale one keeps it.
    txn.needs_review = currency != "USD" and conversion.stale


def create_transaction(db: Session, body: TransactionCreate) -> Transaction:
    if body.kind not in MANUAL_KINDS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{body.kind.value} cannot be created here",
        )
    account = _require_account(db, body.account_id)
    _check_category(db, body.category_id)

    txn = Transaction(
        date=body.date,
        account_id=account.id,
        kind=body.kind,
        direction=_resolve_direction(body.kind, body.direction),
        amount=body.amount,
        category_id=body.category_id,
        merchant_raw=body.merchant_raw,
        merchant_clean=body.merchant_clean,
        description=body.description,
        notes=body.notes,
        is_reimbursable=body.is_reimbursable,
        excluded_from_my_budget=body.excluded_from_my_budget,
        tags=list(body.tags),
    )
    _apply_conversion(db, txn, account.currency.value, body.date)
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def update_transaction(
    db: Session, txn: Transaction, body: TransactionUpdate
) -> Transaction:
    data = body.model_dump(exclude_unset=True)

    if "category_id" in data:
        _check_category(db, data["category_id"])

    account = (
        _require_account(db, data["account_id"])
        if "account_id" in data
        else db.get(Account, txn.account_id)
    )

    for field in (
        "merchant_raw",
        "merchant_clean",
        "description",
        "notes",
        "is_reimbursable",
        "excluded_from_my_budget",
        "category_id",
        "tags",
        "date",
        "account_id",
    ):
        if field in data:
            setattr(txn, field, data[field])

    if "kind" in data or "direction" in data:
        kind = data.get("kind", txn.kind)
        txn.kind = kind
        txn.direction = _resolve_direction(kind, data.get("direction"))

    if "amount" in data:
        txn.amount = data["amount"]

    # Recompute the persisted USD value if anything it depends on moved
    # (this also refreshes needs_review from the current rate situation).
    if {"amount", "account_id", "date"} & data.keys():
        _apply_conversion(db, txn, account.currency.value, txn.date)

    # An explicit needs_review in the request always wins.
    if "needs_review" in data:
        txn.needs_review = data["needs_review"]

    db.commit()
    db.refresh(txn)
    return txn
