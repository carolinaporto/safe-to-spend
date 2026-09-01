"""merchant_rules and import_batches

Revision ID: 343f1317eca6
Revises: ae7513bba466
Create Date: 2026-09-01 09:00:16.431478
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "343f1317eca6"
down_revision: str | None = "ae7513bba466"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TXN_FK = "fk_transactions_import_batch_id"


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("parser", sa.String(length=20), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "merchant_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column(
            "match_type",
            sa.Enum(
                "contains",
                "regex",
                name="merchantmatchtype",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("merchant_clean", sa.String(length=120), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        _TXN_FK,
        "transactions",
        "import_batches",
        ["import_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(_TXN_FK, "transactions", type_="foreignkey")
    op.drop_table("merchant_rules")
    op.drop_table("import_batches")
