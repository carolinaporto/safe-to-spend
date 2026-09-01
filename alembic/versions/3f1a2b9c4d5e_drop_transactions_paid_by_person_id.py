"""drop transactions.paid_by_person_id

The shared-expense model settled on `expense_shares` (my slice implicit)
plus account ownership for external cards, so the original
`paid_by_person_id` column is unused. No code reads or writes it.

Revision ID: 3f1a2b9c4d5e
Revises: 2cadcf21da7f
Create Date: 2026-09-01 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3f1a2b9c4d5e"
down_revision: str | None = "2cadcf21da7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK = "transactions_paid_by_person_id_fkey"


def upgrade() -> None:
    op.drop_constraint(_FK, "transactions", type_="foreignkey")
    op.drop_column("transactions", "paid_by_person_id")


def downgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("paid_by_person_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        _FK,
        "transactions",
        "people",
        ["paid_by_person_id"],
        ["id"],
        ondelete="SET NULL",
    )
