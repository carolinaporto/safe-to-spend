import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models._types import Money


class Budget(Base):
    """A monthly ceiling. ``category_id`` NULL is the global monthly ceiling
    (spec section 3); a set ``category_id`` is a per-category budget."""

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[dt.date] = mapped_column(Date)  # first day of the month
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    amount_usd: Mapped[Money] = mapped_column(default=Decimal("0.00"))
    rollover: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index(
            "uq_budgets_month_global",
            "month",
            unique=True,
            postgresql_where="category_id IS NULL",
        ),
        Index(
            "uq_budgets_month_category",
            "month",
            "category_id",
            unique=True,
            postgresql_where="category_id IS NOT NULL",
        ),
    )
