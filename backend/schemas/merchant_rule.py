from pydantic import BaseModel, Field

from backend.models.enums import MerchantMatchType
from backend.schemas.common import ApiModel


class MerchantRuleCreate(BaseModel):
    pattern: str = Field(min_length=1, max_length=200)
    match_type: MerchantMatchType = MerchantMatchType.contains
    category_id: int | None = None
    merchant_clean: str | None = Field(default=None, max_length=120)
    priority: int = 100


class MerchantRuleUpdate(BaseModel):
    pattern: str | None = Field(default=None, min_length=1, max_length=200)
    match_type: MerchantMatchType | None = None
    category_id: int | None = None
    merchant_clean: str | None = Field(default=None, max_length=120)
    priority: int | None = None


class MerchantRuleOut(ApiModel):
    id: int
    pattern: str
    match_type: MerchantMatchType
    category_id: int | None
    merchant_clean: str | None
    priority: int
    hit_count: int


class RuleSuggestion(BaseModel):
    pattern: str
    match_type: str
    merchant_clean: str | None
