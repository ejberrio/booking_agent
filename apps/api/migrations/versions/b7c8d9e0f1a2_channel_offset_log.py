"""channel offset log (feature 013: ajuste de precio por canal)

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-07-02 20:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b7c8d9e0f1a2'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # El enum changeorigin ya existe (feature 003) → create_type=False.
    origin = postgresql.ENUM(
        'chat', 'manual', 'suggestion', 'rollback', name='changeorigin', create_type=False
    )
    op.create_table(
        'channel_offset_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('channel.id'), nullable=False),
        sa.Column('before_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('after_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('origin', origin, nullable=False, server_default='manual'),
        sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        op.f('ix_channel_offset_log_channel_id'), 'channel_offset_log', ['channel_id']
    )
    op.create_index(
        op.f('ix_channel_offset_log_changed_at'), 'channel_offset_log', ['changed_at']
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_channel_offset_log_changed_at'), table_name='channel_offset_log')
    op.drop_index(op.f('ix_channel_offset_log_channel_id'), table_name='channel_offset_log')
    op.drop_table('channel_offset_log')
