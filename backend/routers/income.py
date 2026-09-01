import datetime as dt

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import require_auth
from backend.schemas.common import MoneyStr
from backend.services.income import income_summary

router = APIRouter(
    prefix="/api/income", tags=["income"], dependencies=[Depends(require_auth)]
)


class IncomeEntry(BaseModel):
    id: int
    date: dt.date
    account_id: int
    amount: MoneyStr
    currency: str
    amount_usd: MoneyStr


class IncomeSummaryOut(BaseModel):
    total_funding_brl: MoneyStr
    total_funding_usd: MoneyStr
    converted_brl: MoneyStr
    converted_usd: MoneyStr
    still_in_brl: MoneyStr
    still_in_brl_usd: MoneyStr
    cumulative_fx_cost_usd: MoneyStr
    entries: list[IncomeEntry]


@router.get("/summary", response_model=IncomeSummaryOut)
def summary(db: Session = Depends(get_db)) -> dict:
    return income_summary(db)
