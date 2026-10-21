"""fecha de la última carga de cada percentil de mercado (feature 040)

Solo agrega una columna opcional: volver a la versión anterior del código es seguro.

Revision ID: d0e1f2a3b4c6
Revises: c9d0e1f2a3b5
Create Date: 2026-10-21 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'd0e1f2a3b4c6'
down_revision: str | None = 'c9d0e1f2a3b5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('market_band', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('market_band', 'updated_at')
