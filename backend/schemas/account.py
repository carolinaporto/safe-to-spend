import datetime as dt

from pydantic import BaseModel, Field

from backend.models.enums import AccountKind, Currency
from backend.schemas.common import ApiModel, MoneyStr


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    institution: str = Field(default="", max_length=120)
    kind: AccountKind
    currency: Currency
    opening_balance: MoneyStr = Field(default="0")
    opening_date: dt.date
    statement_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)
    color: str = Field(default="", max_length=16)
    icon: str = Field(default="", max_length=40)
    is_active: bool = True
    sort_order: int = 0
    owner_person_id: int | None = None


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    institution: str | None = Field(default=None, max_length=120)
    kind: AccountKind | None = None
    currency: Currency | None = None
    opening_balance: MoneyStr | None = None
    opening_date: dt.date | None = None
    statement_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)
    color: str | None = Field(default=None, max_length=16)
    icon: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None
    sort_order: int | None = None
    owner_person_id: int | None = None


class AccountOut(ApiModel):
    id: int
    name: str
    institution: str
    kind: AccountKind
    currency: Currency
    opening_balance: MoneyStr
    opening_date: dt.date
    statement_day: int | None
    due_day: int | None
    color: str
    icon: str
    is_active: bool
    sort_order: int
    owner_person_id: int | None
    is_owned: bool
    balance: MoneyStr
    balance_usd: MoneyStr
