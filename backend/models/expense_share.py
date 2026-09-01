from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models._types import Money


class ExpenseShare(Base):
    """A slice of a transaction that belongs to another person.

    - On a shared expense I paid: they owe me ``share_amount_usd`` (receivable).
    - On an ``external`` account purchase treated as "I owe it back": I owe the
      account's owner ``share_amount_usd`` (liability).

    Settling creates a linked ``income`` (or expense) transaction and sets
    ``settled`` + ``settled_transaction_id`` (spec 4.3).
    """

    __tablename__ = "expense_shares"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE")
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE")
    )
    share_amount_usd: Mapped[Money]
    settled: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL")
    )
