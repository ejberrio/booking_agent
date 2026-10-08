"""webhook events + booking.external_ref único (feature 020: reservas en tiempo real)

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-10-08 18:00:00.000000

Producción verificada sin external_ref duplicados antes de crear el índice único.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a4b5c6d7e8f9'
down_revision: str | None = 'f3a4b5c6d7e8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'webhook_event',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(20), nullable=False, server_default='beds24'),
        sa.Column('result', sa.String(10), nullable=False),
        sa.Column('booking_ref', sa.String(40), nullable=True),
        sa.Column('detail', sa.String(200), nullable=True),
        sa.Column('sync_run_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_webhook_event_received_at'), 'webhook_event', ['received_at'])
    op.create_index('uq_booking_external_ref', 'booking', ['external_ref'], unique=True)


def downgrade() -> None:
    op.drop_index('uq_booking_external_ref', table_name='booking')
    op.drop_index(op.f('ix_webhook_event_received_at'), table_name='webhook_event')
    op.drop_table('webhook_event')
