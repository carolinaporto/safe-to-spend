from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base
from backend.models._types import Money


class ExpenseShare(Base):
    """A slice of a transaction tied to another person.

    - ``i_owe`` false: they owe me ``share_amount_usd`` (a receivable) — their
      slice of an expense I fronted.
    - ``i_owe`` true: I owe this person ``share_amount_usd`` (a liability) —
      e.g. the full charge on their credit card that I put through.

    A single transaction can carry both: a purchase on Dad's card split with
    roommates has one ``i_owe`` liability to Dad for the whole charge plus a
    receivable per roommate.

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
    # true: I owe them; false: they owe me.
    i_owe: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    settled: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL")
    )
