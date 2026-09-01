import datetime as dt
from decimal import Decimal

from sqlalchemy import Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models._types import Money

# Row id of the single plan_config row.
PLAN_CONFIG_ID = 1


class PlanConfig(Base):
    """Single-row table holding the academic-year window, the emergency
    reserve, and the list of future committed costs (spec section 3)."""

    __tablename__ = "plan_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=PLAN_CONFIG_ID)
    academic_year_start: Mapped[dt.date] = mapped_column(Date)
    academic_year_end: Mapped[dt.date] = mapped_column(Date)
    emergency_reserve_usd: Mapped[Money] = mapped_column(default=Decimal("0.00"))
    # [{"label": str, "amount_usd": "1234.56", "due_date": "2026-01-10"}, ...]
    committed_costs: Mapped[list[dict]] = mapped_column(
        JSONB, default=list
    )
