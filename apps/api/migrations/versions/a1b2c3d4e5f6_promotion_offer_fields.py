"""promotion offer fields (feature 011: promos via fixed price)

Revision ID: a1b2c3d4e5f6
Revises: 7d3816a7c205
Create Date: 2026-07-01 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '7d3816a7c205'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('promotion', sa.Column('unit_type_id', sa.Integer(), nullable=True))
    op.add_column('promotion', sa.Column('offer_id', sa.Integer(), nullable=True))
    op.add_column('promotion', sa.Column('external_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_promotion_unit_type_id'), 'promotion', ['unit_type_id'], unique=False
    )
    op.create_foreign_key(
        'fk_promotion_unit_type_id', 'promotion', 'unit_type', ['unit_type_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_promotion_unit_type_id', 'promotion', type_='foreignkey')
    op.drop_index(op.f('ix_promotion_unit_type_id'), table_name='promotion')
    op.drop_column('promotion', 'external_id')
    op.drop_column('promotion', 'offer_id')
    op.drop_column('promotion', 'unit_type_id')
