import datetime as dt

from pydantic import BaseModel, Field

from backend.schemas.common import ApiModel, MoneyStr


class CommittedCost(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    amount_usd: MoneyStr = Field(gt=0)
    due_date: dt.date


class PlanConfigOut(ApiModel):
    academic_year_start: dt.date
    academic_year_end: dt.date
    emergency_reserve_usd: MoneyStr
    committed_costs: list[CommittedCost]


class PlanConfigUpdate(BaseModel):
    academic_year_start: dt.date | None = None
    academic_year_end: dt.date | None = None
    emergency_reserve_usd: MoneyStr | None = Field(default=None, ge=0)
    committed_costs: list[CommittedCost] | None = None
