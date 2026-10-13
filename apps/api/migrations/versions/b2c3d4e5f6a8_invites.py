"""invitaciones y ajustes de plataforma (feature 026, entrega 3)

Solo agrega tablas: volver a la versión anterior del código es seguro.

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-10-13 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a8'
down_revision: str | None = 'a1b2c3d4e5f7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'invite_code',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code_hash', sa.String(64), nullable=False),
        sa.Column('last4', sa.String(4), nullable=False),
        sa.Column('note', sa.String(200), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('app_user.id'), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_by_account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_invite_code_code_hash', 'invite_code', ['code_hash'], unique=True)
    op.create_table(
        'platform_setting',
        sa.Column('key', sa.String(64), primary_key=True),
        sa.Column('value', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('platform_setting')
    op.drop_index('ix_invite_code_code_hash', table_name='invite_code')
    op.drop_table('invite_code')
