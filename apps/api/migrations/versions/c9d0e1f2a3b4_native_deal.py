"""native deal (feature 015: registro informativo de deals nativos de los canales)

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-07-03 21:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c9d0e1f2a3b4'
down_revision: str | None = 'b7c8d9e0f1a2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # El enum channelkind ya existe (feature 001) → create_type=False.
    channel = postgresql.ENUM('booking', 'airbnb', 'direct', name='channelkind', create_type=False)
    op.create_table(
        'native_deal',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel', channel, nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('discount_pct', sa.Numeric(5, 2), nullable=False),
        sa.Column('date_from', sa.Date(), nullable=True),
        sa.Column('date_to', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('native_deal')
