import csv
import datetime as dt
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth
from backend.models.category import Category
from backend.models.enums import CategoryNature, TransactionKind
from backend.models.transaction import Transaction
from backend.schemas.transaction import (
    BulkCategorize,
    TransactionCreate,
    TransactionOut,
    TransactionPage,
    TransactionUpdate,
)
from backend.services.transactions import create_transaction, update_transaction

router = APIRouter(
    prefix="/api/transactions",
    tags=["transactions"],
    dependencies=[Depends(require_auth)],
)


def _filtered(
    *,
    date_from: dt.date | None,
    date_to: dt.date | None,
    account: int | None,
    category: int | None,
    kind: TransactionKind | None,
    currency: str | None,
    nature: CategoryNature | None,
    q: str | None,
) -> Select:
    stmt = select(Transaction)
    if date_from is not None:
        stmt = stmt.where(Transaction.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Transaction.date <= date_to)
    if account is not None:
        stmt = stmt.where(Transaction.account_id == account)
    if category is not None:
        stmt = stmt.where(Transaction.category_id == category)
    if kind is not None:
        stmt = stmt.where(Transaction.kind == kind)
    if currency is not None:
        stmt = stmt.where(Transaction.currency == currency.upper())
    if nature is not None:
        stmt = stmt.where(
            Transaction.category_id.in_(
                select(Category.id).where(Category.nature == nature)
            )
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Transaction.merchant_raw.ilike(like),
                Transaction.merchant_clean.ilike(like),
                Transaction.description.ilike(like),
                Transaction.notes.ilike(like),
            )
        )
    return stmt


def _common_filters(
    date_from: dt.date | None = Query(default=None, alias="from"),
    date_to: dt.date | None = Query(default=None, alias="to"),
    account: int | None = None,
    category: int | None = None,
    kind: TransactionKind | None = None,
    currency: str | None = None,
    nature: CategoryNature | None = None,
    q: str | None = None,
) -> dict:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "account": account,
        "category": category,
        "kind": kind,
        "currency": currency,
        "nature": nature,
        "q": q,
    }


@router.get("", response_model=TransactionPage)
def list_transactions(
    filters: dict = Depends(_common_filters),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> TransactionPage:
    base = _filtered(**filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (
        db.execute(
            base.order_by(Transaction.date.desc(), Transaction.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return TransactionPage(
        items=list(rows), total=total, page=page, page_size=page_size
    )


@router.get("/export")
def export_transactions(
    filters: dict = Depends(_common_filters), db: Session = Depends(get_db)
) -> Response:
    rows = (
        db.execute(
            _filtered(**filters).order_by(
                Transaction.date.desc(), Transaction.id.desc()
            )
        )
        .scalars()
        .all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "date",
            "account_id",
            "direction",
            "kind",
            "amount",
            "currency",
            "fx_rate_to_usd",
            "amount_usd",
            "category_id",
            "merchant",
            "description",
            "notes",
        ]
    )
    for t in rows:
        writer.writerow(
            [
                t.id,
                t.date.isoformat(),
                t.account_id,
                t.direction.value,
                t.kind.value,
                format(t.amount, "f"),
                t.currency,
                format(t.fx_rate_to_usd, "f"),
                format(t.amount_usd, "f"),
                t.category_id or "",
                t.merchant_clean or t.merchant_raw or "",
                t.description,
                t.notes,
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=transactions.csv"
        },
    )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create(body: TransactionCreate, db: Session = Depends(get_db)) -> Transaction:
    return create_transaction(db, body)


@router.patch("/{transaction_id}", response_model=TransactionOut)
def patch(
    transaction_id: int,
    body: TransactionUpdate,
    db: Session = Depends(get_db),
) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "transaction not found")
    return update_transaction(db, txn, body)


@router.post("/bulk-categorize", dependencies=[Depends(deny_in_demo)])
def bulk_categorize(
    body: BulkCategorize, db: Session = Depends(get_db)
) -> dict:
    if body.category_id is not None and db.get(Category, body.category_id) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown category_id"
        )
    updated = (
        db.query(Transaction)
        .filter(Transaction.id.in_(body.transaction_ids))
        .update(
            {Transaction.category_id: body.category_id},
            synchronize_session=False,
        )
    )
    db.commit()
    return {"updated": updated}


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(deny_in_demo)],
)
def delete(transaction_id: int, db: Session = Depends(get_db)) -> None:
    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "transaction not found")
    db.delete(txn)
    db.commit()
