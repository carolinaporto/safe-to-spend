import datetime as dt

from pydantic import BaseModel, Field

from backend.schemas.common import ApiModel, MoneyStr, RateStr


class TransferCreate(BaseModel):
    date: dt.date = Field(default_factory=dt.date.today)
    from_account_id: int
    to_account_id: int
    amount_out: MoneyStr = Field(gt=0)
    amount_in: MoneyStr = Field(gt=0)
    currency_out: str | None = Field(default=None, min_length=3, max_length=3)
    currency_in: str | None = Field(default=None, min_length=3, max_length=3)
    explicit_fee: MoneyStr | None = Field(default=None, ge=0)
    explicit_fee_currency: str | None = Field(
        default=None, min_length=3, max_length=3
    )
    market_rate: RateStr | None = None
    provider: str = Field(default="", max_length=60)
    notes: str = ""


class TransferOut(ApiModel):
    id: int
    transfer_group_id: str
    date: dt.date
    from_account_id: int
    to_account_id: int
    amount_out: MoneyStr
    currency_out: str
    amount_in: MoneyStr
    currency_in: str
    explicit_fee: MoneyStr | None
    explicit_fee_currency: str | None
    effective_rate: RateStr
    market_rate: RateStr
    fx_cost_usd: MoneyStr
    provider: str
    notes: str


class ProviderSummary(BaseModel):
    provider: str
    count: int
    fx_cost_usd: MoneyStr
    avg_effective_rate: RateStr


class TransferSummary(BaseModel):
    count: int
    total_fx_cost_usd: MoneyStr
    providers: list[ProviderSummary]
