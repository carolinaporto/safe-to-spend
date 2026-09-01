import datetime as dt

from pydantic import BaseModel, Field

from backend.models.enums import RecurringFrequency
from backend.schemas.common import ApiModel, MoneyStr


class RecurringRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    account_id: int
    category_id: int | None = None
    amount: MoneyStr = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    frequency: RecurringFrequency
    day_of_month: int = Field(default=1, ge=1, le=31)
    start_date: dt.date
    end_date: dt.date | None = None
    auto_create: bool = True
    is_income: bool = False


class RecurringRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    account_id: int | None = None
    category_id: int | None = None
    amount: MoneyStr | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    frequency: RecurringFrequency | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    auto_create: bool | None = None
    is_income: bool | None = None


class RecurringRuleOut(ApiModel):
    id: int
    name: str
    account_id: int
    category_id: int | None
    amount: MoneyStr
    currency: str
    frequency: RecurringFrequency
    day_of_month: int
    start_date: dt.date
    end_date: dt.date | None
    auto_create: bool
    is_income: bool
    last_generated_date: dt.date | None
