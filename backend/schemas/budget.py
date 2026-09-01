import datetime as dt

from pydantic import BaseModel, Field

from backend.schemas.common import ApiModel, MoneyStr


class BudgetLineOut(ApiModel):
    category_id: int | None
    name: str
    nature: str | None
    amount_usd: MoneyStr
    rollover: bool
    rollover_in_usd: MoneyStr
    spent_usd: MoneyStr
    remaining_usd: MoneyStr


class MonthBudgetOut(ApiModel):
    month: dt.date
    lines: list[BudgetLineOut]


class BudgetEntryIn(BaseModel):
    category_id: int | None = None
    amount_usd: MoneyStr = Field(ge=0)
    rollover: bool = False


class MonthBudgetIn(BaseModel):
    entries: list[BudgetEntryIn]
