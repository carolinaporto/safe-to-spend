import datetime as dt

from pydantic import BaseModel, Field

from backend.models.enums import (
    TransactionDirection,
    TransactionKind,
    TransactionSource,
)
from backend.schemas.common import ApiModel, MoneyStr, RateStr

# Phase 1 records movements directly; transfers (two linked legs) land in Phase 4.
MANUAL_KINDS = {
    TransactionKind.expense,
    TransactionKind.income,
    TransactionKind.adjustment,
}


class TransactionCreate(BaseModel):
    date: dt.date = Field(default_factory=dt.date.today)
    account_id: int
    kind: TransactionKind = TransactionKind.expense
    direction: TransactionDirection | None = None
    amount: MoneyStr = Field(gt=0)
    category_id: int | None = None
    merchant_raw: str | None = None
    merchant_clean: str | None = None
    description: str = ""
    notes: str = ""
    is_reimbursable: bool = False
    excluded_from_my_budget: bool = False
    tags: list[str] = Field(default_factory=list)


class TransactionUpdate(BaseModel):
    date: dt.date | None = None
    account_id: int | None = None
    kind: TransactionKind | None = None
    direction: TransactionDirection | None = None
    amount: MoneyStr | None = Field(default=None, gt=0)
    category_id: int | None = None
    merchant_raw: str | None = None
    merchant_clean: str | None = None
    description: str | None = None
    notes: str | None = None
    is_reimbursable: bool | None = None
    excluded_from_my_budget: bool | None = None
    needs_review: bool | None = None
    tags: list[str] | None = None


class TransactionOut(ApiModel):
    id: int
    date: dt.date
    account_id: int
    direction: TransactionDirection
    kind: TransactionKind
    amount: MoneyStr
    currency: str
    fx_rate_to_usd: RateStr
    amount_usd: MoneyStr
    category_id: int | None
    merchant_raw: str | None
    merchant_clean: str | None
    description: str
    notes: str
    is_shared: bool
    is_reimbursable: bool
    excluded_from_my_budget: bool
    source: TransactionSource
    needs_review: bool
    tags: list[str]
    created_at: dt.datetime
    updated_at: dt.datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


class BulkCategorize(BaseModel):
    transaction_ids: list[int] = Field(min_length=1)
    category_id: int | None
