"""selección de habitaciones de Beds24 y salud de la conexión (feature 044, #150)

Solo agrega columnas opcionales: volver a la versión anterior del código es seguro.

Revision ID: a95edc007861
Revises: 0b5c228ff717
Create Date: 2026-11-05 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'a95edc007861'
down_revision: str | None = '0b5c228ff717'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column('channel_manager_connection', sa.Column('selected_rooms', _JSON, nullable=True))
    op.add_column('channel_manager_connection',
                  sa.Column('invalid_since', sa.DateTime(timezone=True), nullable=True))
    op.add_column('channel_manager_connection', sa.Column('last_error', sa.String(200), nullable=True))
    op.add_column('channel_manager_connection',
                  sa.Column('alerted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('channel_manager_connection',
                  sa.Column('reminded_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ('reminded_at', 'alerted_at', 'last_error', 'invalid_since', 'selected_rooms'):
        op.drop_column('channel_manager_connection', col)
