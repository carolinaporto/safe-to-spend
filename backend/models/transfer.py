import datetime as dt

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models._types import Money, Rate, TimestampCreated


class Transfer(Base):
    """Metadata for a conversion / move between accounts. The two ledger legs
    live in ``transactions`` linked by ``transfer_group_id`` (spec 4.2)."""

    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_group_id: Mapped[str] = mapped_column(String(36))
    date: Mapped[dt.date] = mapped_column(Date)

    from_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT")
    )
    to_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT")
    )

    amount_out: Mapped[Money]
    currency_out: Mapped[str] = mapped_column(String(3))
    amount_in: Mapped[Money]
    currency_in: Mapped[str] = mapped_column(String(3))

    explicit_fee: Mapped[Money | None] = mapped_column()
    explicit_fee_currency: Mapped[str | None] = mapped_column(String(3))

    effective_rate: Mapped[Rate]
    market_rate: Mapped[Rate]
    fx_cost_usd: Mapped[Money]

    provider: Mapped[str] = mapped_column(String(60), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[TimestampCreated]
