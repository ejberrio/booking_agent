"""registro de huéspedes para la TRA y SIRE (feature 046, #167)

Solo crea tablas nuevas: volver a la versión anterior del código es seguro.

Revision ID: 68d46311b5dc
Revises: a95edc007861
Create Date: 2026-11-11 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '68d46311b5dc'
down_revision: str | None = 'a95edc007861'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _ts() -> list[sa.Column]:
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        'guest_registration',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=False),
        sa.Column('booking_id', sa.Integer(), sa.ForeignKey('booking.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('data_encrypted', sa.Text(), nullable=True),
        sa.Column('filled_by', sa.String(10), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cost_cop', sa.Numeric(14, 2), nullable=True),
        sa.Column('tra_code', sa.Integer(), nullable=True),
        sa.Column('tra_companions', _JSON, nullable=True),
        sa.Column('tra_error', sa.String(300), nullable=True),
        sa.Column('tra_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tra_sent_by', sa.Integer(), nullable=True),
        sa.Column('sire_entry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sire_exit_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('purged', sa.Boolean(), nullable=False, server_default=sa.false()),
        *_ts(),
        sa.UniqueConstraint('booking_id', name='uq_guest_registration_booking'),
    )
    op.create_index('ix_guest_registration_account_id', 'guest_registration', ['account_id'])
    op.create_index('ix_guest_registration_booking_id', 'guest_registration', ['booking_id'])
    op.create_index('ix_guest_registration_token', 'guest_registration', ['token'], unique=True)
    op.create_table(
        'registration_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('account.id'), nullable=False),
        sa.Column('rnt', sa.String(20), nullable=True),
        sa.Column('establishment_name', sa.String(120), nullable=True),
        sa.Column('accommodation', _JSON, nullable=True),
        sa.Column('sire_code', sa.String(20), nullable=True),
        sa.Column('sire_city', sa.String(20), nullable=True),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('authorized_by', sa.Integer(), nullable=True),
        *_ts(),
        sa.UniqueConstraint('account_id', name='uq_registration_settings_account'),
    )
    op.create_index('ix_registration_settings_account_id', 'registration_settings', ['account_id'])


def downgrade() -> None:
    op.drop_index('ix_registration_settings_account_id', table_name='registration_settings')
    op.drop_table('registration_settings')
    op.drop_index('ix_guest_registration_token', table_name='guest_registration')
    op.drop_index('ix_guest_registration_booking_id', table_name='guest_registration')
    op.drop_index('ix_guest_registration_account_id', table_name='guest_registration')
    op.drop_table('guest_registration')
