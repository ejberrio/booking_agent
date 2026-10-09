"""avisos al celular (feature 025): push_device + push_notification_log

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-10-09 18:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e8f9a0b1c2d3'
down_revision: str | None = 'd7e8f9a0b1c2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'push_device',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token', sa.String(512), nullable=False),
        sa.Column('platform', sa.String(16), nullable=False, server_default='android'),
        sa.Column('model', sa.String(120), nullable=True),
        sa.Column('app_version', sa.String(32), nullable=True),
        sa.Column('notify_bookings', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notify_suggestions', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_error', sa.String(300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_push_device_token', 'push_device', ['token'], unique=True)
    op.create_table(
        'push_notification_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('ref', sa.String(80), nullable=False),
        sa.Column('fingerprint', sa.String(80), nullable=False),
        sa.Column('sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('kind', 'ref', 'fingerprint', name='uq_push_log_kind_ref_fp'),
    )


def downgrade() -> None:
    op.drop_table('push_notification_log')
    op.drop_index('ix_push_device_token', table_name='push_device')
    op.drop_table('push_device')
