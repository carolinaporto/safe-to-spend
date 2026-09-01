import datetime as dt

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models._types import Money
from backend.models.enums import RecurringFrequency, pg_enum


class RecurringRule(Base):
    """A template that generates transactions on a schedule (spec 3)."""

    __tablename__ = "recurring_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE")
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    amount: Mapped[Money]
    currency: Mapped[str] = mapped_column(String(3))
    frequency: Mapped[RecurringFrequency] = mapped_column(
        pg_enum(RecurringFrequency)
    )
    day_of_month: Mapped[int] = mapped_column(Integer, default=1)
    start_date: Mapped[dt.date] = mapped_column(Date)
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    auto_create: Mapped[bool] = mapped_column(Boolean, default=True)
    last_generated_date: Mapped[dt.date | None] = mapped_column(Date)

    # expense vs income is inferred from the category nature at generation time,
    # but a simple flag keeps it explicit.
    is_income: Mapped[bool] = mapped_column(Boolean, default=False)
