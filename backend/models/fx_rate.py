import datetime as dt

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models._types import Rate


class FxRate(Base):
    """One `base -> quote` conversion rate for a given date.

    ``rate`` means: 1 unit of ``base`` equals ``rate`` units of ``quote``.
    """

    __tablename__ = "fx_rates"

    date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    base: Mapped[str] = mapped_column(String(3), primary_key=True)
    quote: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate: Mapped[Rate]
    source: Mapped[str] = mapped_column(String(40), default="")
