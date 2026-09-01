import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models._types import Money, Rate, TimestampCreated, TimestampUpdated
from backend.models.enums import (
    TransactionDirection,
    TransactionKind,
    TransactionSource,
    pg_enum,
)


class Transaction(Base):
    """One movement in one account (spec invariant 4).

    A transfer between accounts is two rows sharing a ``transfer_group_id``.
    Balances are never stored — they are computed from these rows.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Ledger date: plain DATE, no timezone (spec section 9).
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT")
    )

    direction: Mapped[TransactionDirection] = mapped_column(
        pg_enum(TransactionDirection)
    )
    kind: Mapped[TransactionKind] = mapped_column(pg_enum(TransactionKind))

    # Positive, in the account's currency.
    amount: Mapped[Money]
    currency: Mapped[str] = mapped_column(String(3))
    fx_rate_to_usd: Mapped[Rate] = mapped_column(default=Decimal("1"))
    amount_usd: Mapped[Money]

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )

    merchant_raw: Mapped[str | None] = mapped_column(Text)
    merchant_clean: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    is_shared: Mapped[bool] = mapped_column(default=False)
    is_reimbursable: Mapped[bool] = mapped_column(default=False)
    excluded_from_my_budget: Mapped[bool] = mapped_column(default=False)

    transfer_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    recurring_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurring_rules.id", ondelete="SET NULL")
    )
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL")
    )

    source: Mapped[TransactionSource] = mapped_column(
        pg_enum(TransactionSource), default=TransactionSource.manual
    )
    external_id: Mapped[str | None] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(default=False)

    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    receipt_url: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[TimestampCreated]
    updated_at: Mapped[TimestampUpdated]

    shares: Mapped[list["ExpenseShare"]] = relationship(  # noqa: F821
        "ExpenseShare",
        primaryjoin="Transaction.id == ExpenseShare.transaction_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_transactions_account_date", "account_id", "date"),
        Index("ix_transactions_category_date", "category_id", "date"),
        Index("ix_transactions_transfer_group_id", "transfer_group_id"),
        Index(
            "uq_transactions_account_external_id",
            "account_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )
