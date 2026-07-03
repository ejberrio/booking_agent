"""guest name + calendar note (feature 016: detalle de reservas y notas del host)

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-07-03 23:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3a4b5c6'
down_revision: str | None = 'c9d0e1f2a3b4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('booking', sa.Column('guest_name', sa.String(200), nullable=True))
    op.create_table(
        'calendar_note',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('unit_type_id', sa.Integer(), sa.ForeignKey('unit_type.id'), nullable=False),
        sa.Column('date_from', sa.Date(), nullable=False),
        sa.Column('date_to', sa.Date(), nullable=False),
        sa.Column('text', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_calendar_note_unit_type_id'), 'calendar_note', ['unit_type_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_calendar_note_unit_type_id'), table_name='calendar_note')
    op.drop_table('calendar_note')
    op.drop_column('booking', 'guest_name')
