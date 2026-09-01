"""transfers, expense_shares, recurring_rules

Revision ID: 2cadcf21da7f
Revises: 343f1317eca6
Create Date: 2026-09-01 10:05:37.543306
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2cadcf21da7f"
down_revision: str | None = "343f1317eca6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACCT_OWNER_FK = "fk_accounts_owner_person_id"
_TXN_RECURRING_FK = "fk_transactions_recurring_id"


def upgrade() -> None:
    op.create_table(
        "recurring_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "frequency",
            sa.Enum(
                "weekly",
                "monthly",
                "yearly",
                name="recurringfrequency",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("auto_create", sa.Boolean(), nullable=False),
        sa.Column("last_generated_date", sa.Date(), nullable=True),
        sa.Column("is_income", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "transfers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transfer_group_id", sa.String(length=36), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("from_account_id", sa.Integer(), nullable=False),
        sa.Column("to_account_id", sa.Integer(), nullable=False),
        sa.Column("amount_out", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency_out", sa.String(length=3), nullable=False),
        sa.Column("amount_in", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency_in", sa.String(length=3), nullable=False),
        sa.Column("explicit_fee", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("explicit_fee_currency", sa.String(length=3), nullable=True),
        sa.Column(
            "effective_rate", sa.Numeric(precision=18, scale=8), nullable=False
        ),
        sa.Column(
            "market_rate", sa.Numeric(precision=18, scale=8), nullable=False
        ),
        sa.Column("fx_cost_usd", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["from_account_id"], ["accounts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["to_account_id"], ["accounts.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "expense_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column(
            "share_amount_usd", sa.Numeric(precision=14, scale=2), nullable=False
        ),
        sa.Column("settled", sa.Boolean(), nullable=False),
        sa.Column("settled_transaction_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["person_id"], ["people.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["settled_transaction_id"],
            ["transactions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "accounts", sa.Column("owner_person_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        _ACCT_OWNER_FK,
        "accounts",
        "people",
        ["owner_person_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        _TXN_RECURRING_FK,
        "transactions",
        "recurring_rules",
        ["recurring_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(_TXN_RECURRING_FK, "transactions", type_="foreignkey")
    op.drop_constraint(_ACCT_OWNER_FK, "accounts", type_="foreignkey")
    op.drop_column("accounts", "owner_person_id")
    op.drop_table("expense_shares")
    op.drop_table("transfers")
    op.drop_table("recurring_rules")
