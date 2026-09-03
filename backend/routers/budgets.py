import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth
from backend.schemas.budget import BudgetLineOut, MonthBudgetIn, MonthBudgetOut
from backend.services.budgets import (
    copy_from_previous,
    get_month_budget,
    parse_month,
    put_month_budget,
)

router = APIRouter(
    prefix="/api/budgets", tags=["budgets"], dependencies=[Depends(require_auth)]
)


def _month(month: str) -> dt.date:
    try:
        return parse_month(month)
    except (ValueError, IndexError):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "month must be YYYY-MM or YYYY-MM-DD",
        ) from None


def _serialize(db: Session, month: dt.date) -> MonthBudgetOut:
    return MonthBudgetOut(
        month=month,
        lines=[
            BudgetLineOut.model_validate(line)
            for line in get_month_budget(db, month)
        ],
    )


@router.get("/{month}", response_model=MonthBudgetOut)
def read_month(month: str, db: Session = Depends(get_db)) -> MonthBudgetOut:
    return _serialize(db, _month(month))


@router.put(
    "/{month}",
    response_model=MonthBudgetOut,
    dependencies=[Depends(deny_in_demo)],
)
def write_month(
    month: str, body: MonthBudgetIn, db: Session = Depends(get_db)
) -> MonthBudgetOut:
    parsed = _month(month)
    put_month_budget(
        db,
        parsed,
        [(e.category_id, e.amount_usd, e.rollover) for e in body.entries],
    )
    return _serialize(db, parsed)


@router.post(
    "/{month}/copy-from-previous",
    response_model=MonthBudgetOut,
    dependencies=[Depends(deny_in_demo)],
)
def copy_previous(month: str, db: Session = Depends(get_db)) -> MonthBudgetOut:
    parsed = _month(month)
    copied = copy_from_previous(db, parsed)
    if copied == 0:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "no budget to copy from the previous month"
        )
    return _serialize(db, parsed)
