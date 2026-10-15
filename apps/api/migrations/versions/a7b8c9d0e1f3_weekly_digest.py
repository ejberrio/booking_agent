"""resumen semanal por correo: preferencia del usuario y último envío por cuenta (feature 030)

Solo agrega columnas con valor por defecto: volver a la versión anterior del código es seguro.

Revision ID: a7b8c9d0e1f3
Revises: f6a7b8c9d0e2
Create Date: 2026-10-14 17:05:42.085022

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'a7b8c9d0e1f3'
down_revision: str | None = 'f6a7b8c9d0e2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('account', sa.Column('digest_sent_on', sa.Date(), nullable=True))
    op.add_column('app_user', sa.Column('weekly_digest', sa.Boolean(), server_default='true', nullable=False))


def downgrade() -> None:
    op.drop_column('app_user', 'weekly_digest')
    op.drop_column('account', 'digest_sent_on')
