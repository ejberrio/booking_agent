"""acceso por usuario (feature 026, entrega 2): usuarios, membresías, sesiones, enlaces

Solo agrega tablas y columnas (nada se borra): volver a la versión anterior del código es
seguro. La cuenta nº 1 queda sin usuario hasta que el host la reclame.

Revision ID: a1b2c3d4e5f7
Revises: f9a0b1c2d3e4
Create Date: 2026-10-13 15:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f7'
down_revision: str | None = 'f9a0b1c2d3e4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAMPED = [
    'price_change_log', 'promotion_change_log', 'channel_offset_log', 'availability_change_log',
    'conversation', 'agent_action', 'push_device', 'secret_change_log',
]


def _ts():
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        'app_user',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('google_sub', sa.String(64), nullable=True),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('language', sa.String(5), nullable=False, server_default='es'),
        sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.UniqueConstraint('google_sub', name='app_user_google_sub_key'),
    )
    op.create_index('ix_app_user_email', 'app_user', ['email'], unique=True)

    op.create_table(
        'membership',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=False),
        sa.Column('role', sa.String(16), nullable=False, server_default='owner'),
        *_ts(),
        sa.UniqueConstraint('user_id', 'account_id', name='uq_membership_user_account'),
    )
    op.create_index('ix_membership_user_id', 'membership', ['user_id'])
    op.create_index('ix_membership_account_id', 'membership', ['account_id'])

    op.create_table(
        'user_session',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('kind', sa.String(8), nullable=False, server_default='web'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_agent', sa.String(200), nullable=True),
        *_ts(),
    )
    op.create_index('ix_user_session_user_id', 'user_session', ['user_id'])
    op.create_index('ix_user_session_token_hash', 'user_session', ['token_hash'], unique=True)

    op.create_table(
        'auth_token',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('purpose', sa.String(20), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('app_user.id'), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        *_ts(),
    )
    op.create_index('ix_auth_token_purpose', 'auth_token', ['purpose'])
    op.create_index('ix_auth_token_token_hash', 'auth_token', ['token_hash'], unique=True)

    op.create_table(
        'auth_attempt',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email_hash', sa.String(64), nullable=False),
        sa.Column('ip', sa.String(64), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.false()),
        *_ts(),
    )
    op.create_index('ix_auth_attempt_email_hash', 'auth_attempt', ['email_hash'])
    op.create_index('ix_auth_attempt_ip', 'auth_attempt', ['ip'])

    for table in STAMPED:
        op.add_column(table, sa.Column('user_id', sa.Integer(), nullable=True))
        op.create_foreign_key(f'{table}_user_id_fkey', table, 'app_user', ['user_id'], ['id'])


def downgrade() -> None:
    for table in reversed(STAMPED):
        op.drop_constraint(f'{table}_user_id_fkey', table, type_='foreignkey')
        op.drop_column(table, 'user_id')
    op.drop_table('auth_attempt')
    op.drop_table('auth_token')
    op.drop_table('user_session')
    op.drop_table('membership')
    op.drop_index('ix_app_user_email', table_name='app_user')
    op.drop_table('app_user')
