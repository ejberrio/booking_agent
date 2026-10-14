"""página pública e informe gratis: caché por ciudad, informes, lista de espera, métricas (feature 030)

Solo agrega tablas nuevas y una columna opcional: volver a la versión anterior del código es seguro.

Revision ID: f6a7b8c9d0e2
Revises: e5f6a7b8c9d1
Create Date: 2026-10-14 15:03:20.002629

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'f6a7b8c9d0e2'
down_revision: str | None = 'e5f6a7b8c9d1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('city_scan',
    sa.Column('city', sa.String(length=80), nullable=False),
    sa.Column('scanned_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('source', sa.String(length=10), nullable=False),
    sa.Column('events_found', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('city')
    )
    op.create_table('public_metric',
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('key', sa.String(length=30), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('day', 'key')
    )
    op.create_table('public_quota',
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('visitor', sa.String(length=32), nullable=False),
    sa.Column('kind', sa.String(length=12), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('day', 'visitor', 'kind')
    )
    op.create_table('waitlist_entry',
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('language', sa.String(length=2), nullable=False),
    sa.Column('municipality_code', sa.String(length=5), nullable=True),
    sa.Column('consent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('public_report',
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('municipality_code', sa.String(length=5), nullable=False),
    sa.Column('city', sa.String(length=80), nullable=False),
    sa.Column('weekday_price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('weekend_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('unit_kind', sa.String(length=20), nullable=True),
    sa.Column('language', sa.String(length=2), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('emailed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_public_report_account_id'), 'public_report', ['account_id'], unique=False)
    op.create_index(op.f('ix_public_report_token_hash'), 'public_report', ['token_hash'], unique=True)
    op.add_column('account', sa.Column('signup_source', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('account', 'signup_source')
    op.drop_index(op.f('ix_public_report_token_hash'), table_name='public_report')
    op.drop_index(op.f('ix_public_report_account_id'), table_name='public_report')
    op.drop_table('public_report')
    op.drop_table('waitlist_entry')
    op.drop_table('public_quota')
    op.drop_table('public_metric')
    op.drop_table('city_scan')
