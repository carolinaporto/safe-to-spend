"""Manual transaction creation and editing.

Currency conversion happens here, at write time, and is persisted on the row
(spec invariant 3). Direction follows the kind unless given explicitly.
"""

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.models.category import Category
from backend.models.enums import (
    AccountKind,
    ExternalTreatment,
    TransactionDirection,
    TransactionKind,
)
from backend.models.expense_share import ExpenseShare
from backend.models.person import Person
from backend.models.transaction import Transaction
from backend.money import ZERO
from backend.schemas.transaction import (
    MANUAL_KINDS,
    ShareIn,
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


def _require_person(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown person_id"
        )
    return person


def _set_shares(
    db: Session, txn: Transaction, shares: list[ShareIn]
) -> None:
    """Replace the transaction's expense_shares. Total may not exceed the
    transaction's own USD amount (my share is the remainder)."""
    total = sum((s.share_amount_usd for s in shares), ZERO)
    if total > txn.amount_usd:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "shares exceed the transaction amount",
        )
    txn.shares = [
        ExpenseShare(
            person_id=_require_person(db, s.person_id).id,
            share_amount_usd=s.share_amount_usd,
        )
        for s in shares
    ]


def _apply_external_treatment(
    db: Session, txn: Transaction, body: TransactionCreate, account: Account
) -> None:
    if account.kind != AccountKind.external:
        return
    if body.external_treatment is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "external-account purchases need external_treatment (gift|owe)",
        )
    if body.external_treatment == ExternalTreatment.gift:
        txn.excluded_from_my_budget = True
        return
    # "I owe it back" — a liability against the card's owner.
    owner_id = body.owed_to_person_id or account.owner_person_id
    if owner_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "who do you owe? set owed_to_person_id or the account's owner",
        )
    txn.shares = [
        ExpenseShare(
            person_id=_require_person(db, owner_id).id,
            share_amount_usd=txn.amount_usd,
        )
    ]


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
        is_shared=body.is_shared or bool(body.shares),
        tags=list(body.tags),
    )
    _apply_conversion(db, txn, account.currency.value, body.date)

    if body.shares:
        _set_shares(db, txn, body.shares)
    _apply_external_treatment(db, txn, body, account)

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

    if "is_shared" in data:
        txn.is_shared = data["is_shared"]
    if body.shares is not None:
        _set_shares(db, txn, body.shares)
        txn.is_shared = bool(body.shares)

    db.commit()
    db.refresh(txn)
    return txn
