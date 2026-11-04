"""ocupación típica del mercado por mes (feature 043, issue #185)

Solo agrega una tabla: volver a la versión anterior del código es seguro.

Revision ID: 0b5c228ff717
Revises: 333969cbeb8c
Create Date: 2026-11-04 17:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0b5c228ff717'
down_revision: str | None = '333969cbeb8c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'market_occupancy',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('city', sa.String(80), nullable=False),
        sa.Column('bedrooms', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('occupancy', sa.Numeric(5, 2), nullable=False),
        sa.Column('source', sa.String(40), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('city', 'bedrooms', 'month', name='uq_market_occupancy'),
    )
    op.create_index('ix_market_occupancy_city', 'market_occupancy', ['city'])


def downgrade() -> None:
    op.drop_index('ix_market_occupancy_city', table_name='market_occupancy')
    op.drop_table('market_occupancy')
