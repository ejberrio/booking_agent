"""uso y límites de IA por cuenta (feature 027)

Agrega la tabla `ai_usage` y dos columnas opcionales a `account`: volver a la versión
anterior del código es seguro.

Revision ID: d4e5f6a7b8c0
Revises: c3d4e5f6a7b9
Create Date: 2026-10-14 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c0'
down_revision: str | None = 'c3d4e5f6a7b9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'ai_usage',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('model', sa.String(80), nullable=False),
        sa.Column('calls', sa.Integer(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Numeric(12, 6), nullable=False),
        sa.Column('unpriced', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('account_id', 'day', 'kind', 'model', name='uq_ai_usage_day_kind_model'),
    )
    op.create_index('ix_ai_usage_account_id', 'ai_usage', ['account_id'])
    op.create_index('ix_ai_usage_day', 'ai_usage', ['day'])
    op.add_column('account', sa.Column('chat_limit_month', sa.Integer(), nullable=True))
    op.add_column('account', sa.Column('search_limit_day', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('account', 'search_limit_day')
    op.drop_column('account', 'chat_limit_month')
    op.drop_index('ix_ai_usage_day', table_name='ai_usage')
    op.drop_index('ix_ai_usage_account_id', table_name='ai_usage')
    op.drop_table('ai_usage')
