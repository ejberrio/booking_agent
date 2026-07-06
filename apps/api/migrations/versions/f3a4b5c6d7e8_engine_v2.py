"""engine v2 (feature 018: contexto de propiedad, POIs, scan config, mercado, superseded)

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-04 16:00:00.000000

Nota: el valor 'superseded' del enum suggestionstatus NO se remueve en downgrade
(PostgreSQL no soporta DROP VALUE; es aditivo e inocuo).
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a4b5c6d7e8'
down_revision: str | None = 'e2f3a4b5c6d7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('property', sa.Column('address', sa.String(300), nullable=True))
    op.add_column('property', sa.Column('latitude', sa.Numeric(9, 6), nullable=True))
    op.add_column('property', sa.Column('longitude', sa.Numeric(9, 6), nullable=True))

    op.create_table(
        'point_of_interest',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('note', sa.String(300), nullable=True),
        sa.Column('date_from', sa.Date(), nullable=True),
        sa.Column('date_to', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'scan_config',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('zone', sa.String(200), nullable=True),
        sa.Column('queries_per_scan', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('event_kinds', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column('market_reference', sa.Column('occupancy_pct', sa.Numeric(5, 2), nullable=True))
    op.add_column('market_reference', sa.Column('sample_size', sa.Integer(), nullable=True))

    if op.get_bind().dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE suggestionstatus ADD VALUE IF NOT EXISTS 'superseded'")


def downgrade() -> None:
    op.drop_column('market_reference', 'sample_size')
    op.drop_column('market_reference', 'occupancy_pct')
    op.drop_table('scan_config')
    op.drop_table('point_of_interest')
    op.drop_column('property', 'longitude')
    op.drop_column('property', 'latitude')
    op.drop_column('property', 'address')
