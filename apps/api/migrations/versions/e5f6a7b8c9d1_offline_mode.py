"""modo sin conexión: cuenta manual y enlaces de anuncio/iCal por canal (feature 029)

Solo agrega columnas opcionales: volver a la versión anterior del código es seguro.

Revision ID: e5f6a7b8c9d1
Revises: d4e5f6a7b8c0
Create Date: 2026-10-14 13:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'e5f6a7b8c9d1'
down_revision: str | None = 'd4e5f6a7b8c0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'account',
        sa.Column('channel_mode', sa.String(12), nullable=False, server_default='connected'),
    )
    op.add_column('channel', sa.Column('listing_url', sa.String(500), nullable=True))
    op.add_column('channel', sa.Column('ical_url', sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column('channel', 'ical_url')
    op.drop_column('channel', 'listing_url')
    op.drop_column('account', 'channel_mode')
