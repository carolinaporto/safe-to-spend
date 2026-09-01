"""plan_config and budgets

Revision ID: ae7513bba466
Revises: 857da26561b7
Create Date: 2026-08-31 18:38:53.429233

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ae7513bba466'
down_revision: str | None = '857da26561b7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('plan_config',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('academic_year_start', sa.Date(), nullable=False),
    sa.Column('academic_year_end', sa.Date(), nullable=False),
    sa.Column('emergency_reserve_usd', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('committed_costs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('budgets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('month', sa.Date(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('amount_usd', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('rollover', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_budgets_month_category', 'budgets', ['month', 'category_id'], unique=True, postgresql_where='category_id IS NOT NULL')
    op.create_index('uq_budgets_month_global', 'budgets', ['month'], unique=True, postgresql_where='category_id IS NULL')



def downgrade() -> None:
    op.drop_index('uq_budgets_month_global', table_name='budgets', postgresql_where='category_id IS NULL')
    op.drop_index('uq_budgets_month_category', table_name='budgets', postgresql_where='category_id IS NOT NULL')
    op.drop_table('budgets')
    op.drop_table('plan_config')

