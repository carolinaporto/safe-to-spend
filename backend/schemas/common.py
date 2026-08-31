from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer

from backend.money import money, money_str, rate

# Money in / out of the API: accept string or number, store as a 2-dp Decimal,
# serialize to a plain string so JavaScript never rounds a balance.
MoneyStr = Annotated[
    Decimal,
    BeforeValidator(money),
    PlainSerializer(money_str, return_type=str, when_used="json"),
]

RateStr = Annotated[
    Decimal,
    BeforeValidator(rate),
    PlainSerializer(
        lambda d: format(rate(d), "f"), return_type=str, when_used="json"
    ),
]


class ApiModel(BaseModel):
    """Base for response models read from ORM objects."""

    model_config = ConfigDict(from_attributes=True)
