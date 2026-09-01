import datetime as dt

from pydantic import BaseModel

from backend.schemas.common import ApiModel, MoneyStr


class PreviewRowOut(ApiModel):
    key: str
    date: dt.date
    amount: MoneyStr
    direction: str
    currency: str
    merchant_raw: str
    merchant_clean: str | None
    category_id: int | None
    category_name: str | None
    amount_usd: MoneyStr
    fx_stale: bool
    status: str
    external_id: str | None


class PreviewOut(ApiModel):
    parser: str
    account_id: int
    filename: str
    rows: list[PreviewRowOut]
    summary: dict[str, int]


class CommitOut(ApiModel):
    batch_id: int
    parser: str
    filename: str
    row_count: int
    imported_count: int
    duplicate_count: int


class ReviewQueueItem(ApiModel):
    id: int
    date: dt.date
    account_id: int
    amount: MoneyStr
    currency: str
    amount_usd: MoneyStr
    merchant_raw: str | None
    merchant_clean: str | None
    description: str
    category_id: int | None
    direction: str
    kind: str
    source: str


class ReviewQueueOut(BaseModel):
    items: list[ReviewQueueItem]
    total: int
