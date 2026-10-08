"""bajadas como promoción (feature 022): native_deal.stacking + price_suggestion.applied_promotion_id

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-10-09 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c6d7e8f9a0b1'
down_revision: str | None = 'b5c6d7e8f9a0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'native_deal',
        sa.Column('stacking', sa.String(12), nullable=False, server_default='conditional'),
    )
    # Los descuentos móviles pueden aplicar a cualquier reserva → cuentan para el piso.
    op.execute(
        "UPDATE native_deal SET stacking = 'always' "
        "WHERE lower(name) LIKE '%mobile%' OR lower(name) LIKE '%móvil%' OR lower(name) LIKE '%movil%'"
    )
    op.add_column('price_suggestion', sa.Column('applied_promotion_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('price_suggestion', 'applied_promotion_id')
    op.drop_column('native_deal', 'stacking')
