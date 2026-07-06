"""secret entries + audit (feature 017: gestión de secretos desde la interfaz)

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-04 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e2f3a4b5c6d7'
down_revision: str | None = 'd1e2f3a4b5c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'secret_entry',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(60), nullable=False),
        sa.Column('value_encrypted', sa.Text(), nullable=False),
        sa.Column('hint', sa.String(8), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_secret_entry_name'), 'secret_entry', ['name'], unique=True)
    op.create_table(
        'secret_change_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(60), nullable=False),
        sa.Column('action', sa.String(12), nullable=False),
        sa.Column('hint', sa.String(8), nullable=False, server_default=''),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_secret_change_log_name'), 'secret_change_log', ['name'])
    op.create_index(op.f('ix_secret_change_log_changed_at'), 'secret_change_log', ['changed_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_secret_change_log_changed_at'), table_name='secret_change_log')
    op.drop_index(op.f('ix_secret_change_log_name'), table_name='secret_change_log')
    op.drop_table('secret_change_log')
    op.drop_index(op.f('ix_secret_entry_name'), table_name='secret_entry')
    op.drop_table('secret_entry')
