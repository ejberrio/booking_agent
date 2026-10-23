"""rentabilidad mensual: valor y comisión de cada reserva, costos de la unidad y TRM (feature 042)

Solo agrega columnas opcionales y dos tablas: volver a la versión anterior del código es seguro.

Revision ID: 333969cbeb8c
Revises: d0e1f2a3b4c6
Create Date: 2026-10-23 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '333969cbeb8c'
down_revision: str | None = 'd0e1f2a3b4c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('booking', sa.Column('amount', sa.Numeric(14, 2), nullable=True))
    op.add_column('booking', sa.Column('commission', sa.Numeric(14, 2), nullable=True))
    op.add_column('booking', sa.Column('currency', sa.String(3), nullable=True))
    op.create_table(
        'unit_finance',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=False),
        sa.Column('unit_type_id', sa.Integer(), sa.ForeignKey('unit_type.id'), nullable=False),
        sa.Column('reference_rent', sa.Numeric(14, 2), nullable=True),
        sa.Column('fixed_costs', sa.Numeric(14, 2), nullable=True),
        sa.Column('cleaning_per_stay', sa.Numeric(14, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint('unit_type_id', name='uq_unit_finance_unit'),
    )
    op.create_index('ix_unit_finance_account_id', 'unit_finance', ['account_id'])
    op.create_index('ix_unit_finance_unit_type_id', 'unit_finance', ['unit_type_id'])
    op.create_table(
        'fx_rate',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('quote', sa.String(3), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('rate', sa.Numeric(14, 4), nullable=False),
        sa.Column('source', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint('currency', 'quote', 'day', name='uq_fx_rate'),
    )
    op.create_index('ix_fx_rate_day', 'fx_rate', ['day'])


def downgrade() -> None:
    op.drop_index('ix_fx_rate_day', table_name='fx_rate')
    op.drop_table('fx_rate')
    op.drop_index('ix_unit_finance_unit_type_id', table_name='unit_finance')
    op.drop_index('ix_unit_finance_account_id', table_name='unit_finance')
    op.drop_table('unit_finance')
    op.drop_column('booking', 'currency')
    op.drop_column('booking', 'commission')
    op.drop_column('booking', 'amount')
