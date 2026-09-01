from pydantic import BaseModel, Field

from backend.models.enums import PersonRole
from backend.schemas.common import ApiModel, MoneyStr


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: PersonRole = PersonRole.other
    notes: str = ""


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: PersonRole | None = None
    notes: str | None = None


class PersonOut(ApiModel):
    id: int
    name: str
    role: PersonRole
    notes: str


class PersonBalanceOut(BaseModel):
    person_id: int
    name: str
    role: PersonRole
    owed_to_me_usd: MoneyStr
    i_owe_usd: MoneyStr
    net_usd: MoneyStr


class SettleRequest(BaseModel):
    account_id: int
