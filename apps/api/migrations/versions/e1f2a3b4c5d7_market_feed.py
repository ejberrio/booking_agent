"""carga automática de percentiles desde la API de PriceLabs (feature 041)

Solo agrega una tabla: volver a la versión anterior del código es seguro.

Revision ID: e1f2a3b4c5d7
Revises: d0e1f2a3b4c6
Create Date: 2026-10-21 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'e1f2a3b4c5d7'
down_revision: str | None = 'd0e1f2a3b4c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('market_feed',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city', sa.String(length=80), nullable=False),
    sa.Column('bedrooms', sa.Integer(), nullable=False),
    sa.Column('listing_id', sa.String(length=80), nullable=False),
    sa.Column('pms', sa.String(length=40), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_status', sa.String(length=200), nullable=True),
    sa.Column('last_imported', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('city', 'bedrooms', name='uq_market_feed')
    )


def downgrade() -> None:
    op.drop_table('market_feed')
