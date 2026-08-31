import datetime as dt
from decimal import Decimal
from typing import Annotated

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.orm import mapped_column

# Monetary and rate column types (spec invariant 1).
Money = Annotated[Decimal, mapped_column(Numeric(14, 2))]
Rate = Annotated[Decimal, mapped_column(Numeric(18, 8))]

TimestampCreated = Annotated[
    dt.datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now()),
]
TimestampUpdated = Annotated[
    dt.datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    ),
]
