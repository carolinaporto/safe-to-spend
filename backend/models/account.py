import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models._types import Money
from backend.models.enums import AccountKind, Currency, pg_enum


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    institution: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[AccountKind] = mapped_column(pg_enum(AccountKind))
    currency: Mapped[Currency] = mapped_column(pg_enum(Currency))
    opening_balance: Mapped[Money] = mapped_column(default=Decimal("0.00"))
    opening_date: Mapped[dt.date] = mapped_column(Date)

    # Credit-card statement cycle (used from Phase 4).
    statement_day: Mapped[int | None] = mapped_column(Integer)
    due_day: Mapped[int | None] = mapped_column(Integer)

    color: Mapped[str] = mapped_column(String(16), default="")
    icon: Mapped[str] = mapped_column(String(40), default="")
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # For ``external`` accounts: the person whose card/money this is. An
    # "I owe it back" purchase becomes a liability against them (spec 4.4).
    owner_person_id: Mapped[int | None] = mapped_column(
        ForeignKey("people.id", ondelete="SET NULL")
    )

    @property
    def is_owned(self) -> bool:
        """External accounts are excluded from net worth and runway."""
        return self.kind != AccountKind.external
