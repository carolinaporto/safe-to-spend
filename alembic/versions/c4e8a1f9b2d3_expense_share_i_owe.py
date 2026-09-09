"""expense_shares.i_owe

Make the direction of a share explicit instead of inferring it from the
account kind, so one transaction can carry both a liability to a card owner
and receivables from the people it was split with.

Backfill: shares on a purchase against an ``external`` account are liabilities
(``i_owe`` = true), matching the old account-kind heuristic.

Revision ID: c4e8a1f9b2d3
Revises: 3f1a2b9c4d5e
Create Date: 2026-09-08 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8a1f9b2d3"
down_revision: str | None = "3f1a2b9c4d5e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "expense_shares",
        sa.Column(
            "i_owe",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        """
        UPDATE expense_shares AS es
        SET i_owe = true
        FROM transactions AS t
        JOIN accounts AS a ON a.id = t.account_id
        WHERE es.transaction_id = t.id AND a.kind = 'external'
        """
    )


def downgrade() -> None:
    op.drop_column("expense_shares", "i_owe")
