"""extender precios (feature 023): ChangeOrigin.extension + borrar precios 0

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-10-08 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op


revision: str = 'd7e8f9a0b1c2'
down_revision: str | None = 'c6d7e8f9a0b1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # El enum nativo solo existe en PostgreSQL (en SQLite es VARCHAR).
    if op.get_bind().dialect.name == 'postgresql':
        op.execute("ALTER TYPE changeorigin ADD VALUE IF NOT EXISTS 'extension'")
    # Noches sin precio que la sincronización guardaba como 0: no son precios.
    op.execute("DELETE FROM rate WHERE base_price <= 0")


def downgrade() -> None:
    # PostgreSQL no permite quitar valores de un enum; las filas borradas eran basura.
    pass
