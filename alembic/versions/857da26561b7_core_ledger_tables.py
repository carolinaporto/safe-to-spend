"""core ledger tables

Creates accounts, categories, people, fx_rates and transactions — the
Phase 1 data model (spec section 3). Account balances are never stored;
they are computed from transaction rows.

Revision ID: 857da26561b7
Revises: b0be6ef69ee2
Create Date: 2026-08-30 23:31:51.348799
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "857da26561b7"
down_revision: str | None = "b0be6ef69ee2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("institution", sa.String(length=120), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "checking",
                "savings",
                "credit_card",
                "cash",
                "external",
                name="accountkind",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.Enum(
                "USD",
                "BRL",
                name="currency",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column(
            "opening_balance", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column("opening_date", sa.Date(), nullable=False),
        sa.Column("statement_day", sa.Integer(), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("icon", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column(
            "nature",
            sa.Enum(
                "essential",
                "discretionary",
                "setup",
                "fee",
                "income",
                name="categorynature",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("icon", sa.String(length=40), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "fx_rates",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("base", sa.String(length=3), nullable=False),
        sa.Column("quote", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("date", "base", "quote"),
    )
    op.create_table(
        "people",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "me",
                "roommate",
                "parent",
                "other",
                name="personrole",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column(
            "direction",
            sa.Enum(
                "in",
                "out",
                name="transactiondirection",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "expense",
                "income",
                "transfer",
                "adjustment",
                name="transactionkind",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "fx_rate_to_usd", sa.Numeric(precision=18, scale=8), nullable=False
        ),
        sa.Column(
            "amount_usd", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("merchant_raw", sa.Text(), nullable=True),
        sa.Column("merchant_clean", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("paid_by_person_id", sa.Integer(), nullable=True),
        sa.Column("is_shared", sa.Boolean(), nullable=False),
        sa.Column("is_reimbursable", sa.Boolean(), nullable=False),
        sa.Column("excluded_from_my_budget", sa.Boolean(), nullable=False),
        sa.Column("transfer_group_id", sa.UUID(), nullable=True),
        sa.Column("recurring_id", sa.Integer(), nullable=True),
        sa.Column("import_batch_id", sa.Integer(), nullable=True),
        sa.Column(
            "source",
            sa.Enum(
                "manual",
                "csv",
                "api",
                name="transactionsource",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("receipt_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["paid_by_person_id"], ["people.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transactions_account_date",
        "transactions",
        ["account_id", "date"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_category_date",
        "transactions",
        ["category_id", "date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_date"), "transactions", ["date"], unique=False
    )
    op.create_index(
        "ix_transactions_transfer_group_id",
        "transactions",
        ["transfer_group_id"],
        unique=False,
    )
    op.create_index(
        "uq_transactions_account_external_id",
        "transactions",
        ["account_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_transactions_account_external_id",
        table_name="transactions",
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_transactions_transfer_group_id", table_name="transactions"
    )
    op.drop_index(op.f("ix_transactions_date"), table_name="transactions")
    op.drop_index("ix_transactions_category_date", table_name="transactions")
    op.drop_index("ix_transactions_account_date", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("people")
    op.drop_table("fx_rates")
    op.drop_table("categories")
    op.drop_table("accounts")
