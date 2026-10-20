"""percentiles de mercado por zona/habitaciones/fecha y habitaciones de la unidad (feature 038)

Solo agrega una tabla y una columna opcional: volver a la versión anterior del código es seguro.

Revision ID: c9d0e1f2a3b5
Revises: b8c9d0e1f2a4
Create Date: 2026-10-20 15:19:00.396759

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'c9d0e1f2a3b5'
down_revision: str | None = 'b8c9d0e1f2a4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('market_band',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city', sa.String(length=80), nullable=False),
    sa.Column('bedrooms', sa.Integer(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('p25', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('p50', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('p75', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('p90', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('source', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('city', 'bedrooms', 'day', name='uq_market_band')
    )
    op.create_index(op.f('ix_market_band_city'), 'market_band', ['city'], unique=False)
    op.create_index(op.f('ix_market_band_day'), 'market_band', ['day'], unique=False)
    op.add_column('unit_type', sa.Column('bedrooms', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('unit_type', 'bedrooms')
    op.drop_index(op.f('ix_market_band_day'), table_name='market_band')
    op.drop_index(op.f('ix_market_band_city'), table_name='market_band')
    op.drop_table('market_band')
