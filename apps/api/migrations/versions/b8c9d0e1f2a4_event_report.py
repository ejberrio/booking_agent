"""reportes de eventos faltantes por cuenta (feature 035)

Solo agrega una tabla nueva: volver a la versión anterior del código es seguro.

Revision ID: b8c9d0e1f2a4
Revises: a7b8c9d0e1f3
Create Date: 2026-10-16 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b8c9d0e1f2a4'
down_revision: str | None = 'a7b8c9d0e1f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'event_report',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('venue', sa.String(200), nullable=True),
        sa.Column('status', sa.String(12), nullable=False),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('event.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_event_report_account_id', 'event_report', ['account_id'])
    op.create_index('ix_event_report_start_date', 'event_report', ['start_date'])


def downgrade() -> None:
    op.drop_index('ix_event_report_start_date', table_name='event_report')
    op.drop_index('ix_event_report_account_id', table_name='event_report')
    op.drop_table('event_report')
