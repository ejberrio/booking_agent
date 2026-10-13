"""cuentas y aislamiento (feature 026): account + account_id en las tablas del anfitrión

Todos los datos existentes pasan a la cuenta nº 1 (el host original). En PostgreSQL la
migración es transaccional: si falla a mitad, no queda nada a medias y puede reintentarse.

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-10-10 12:00:00.000000

"""
import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f9a0b1c2d3e4'
down_revision: str | None = 'e8f9a0b1c2d3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FIRST = 1

# Tablas con datos de un anfitrión (mixin AccountOwned).
OWNED = [
    'property', 'unit_type', 'channel', 'calendar_day', 'rate', 'calendar_note', 'booking',
    'price_change_log', 'availability_change_log', 'promotion', 'promotion_change_log',
    'channel_offset_log', 'pricing_rule', 'native_deal', 'price_suggestion',
    'point_of_interest', 'conversation', 'message', 'agent_action', 'push_device',
    'push_notification_log', 'app_preference', 'scan_config', 'intelligence_run', 'sync_run',
    'sync_issue', 'webhook_event', 'channel_manager_connection',
]
ACCOUNT_SECRETS = ('beds24_refresh_token', 'beds24_webhook_key')


def _normalize_city(city: str | None) -> str:
    # Igual que event_service.normalize_city (copiado: una migración no depende del código vivo).
    base = (city or 'Medellín').split(',')[0].strip() or 'Medellín'
    plain = unicodedata.normalize('NFKD', base).encode('ascii', 'ignore').decode()
    return ' '.join(plain.lower().split())


def _dedupe_singleton(table: str, keep: str) -> None:
    """Antes de exigir 'una fila por cuenta', deja una sola (defensivo)."""
    op.execute(sa.text(f'DELETE FROM {table} WHERE id NOT IN (SELECT {keep} FROM {table})'))


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        'account',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column(
            'status',
            sa.Enum('active', 'disabled', name='accountstatus'),
            nullable=False,
            server_default='active',
        ),
        sa.Column('disabled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute(sa.text("INSERT INTO account (id, name, status) VALUES (1, 'Mi cuenta', 'active')"))
    if bind.dialect.name == 'postgresql':
        op.execute(sa.text("SELECT setval(pg_get_serial_sequence('account', 'id'), 1)"))

    # Singletons → una fila por cuenta (defensivo antes de los únicos).
    _dedupe_singleton('app_preference', 'MIN(id)')
    _dedupe_singleton('scan_config', 'MIN(id)')
    _dedupe_singleton('channel_manager_connection', 'MAX(id)')

    for table in OWNED:
        op.add_column(table, sa.Column('account_id', sa.Integer(), nullable=True))
        op.execute(sa.text(f'UPDATE {table} SET account_id = {FIRST}'))
        op.alter_column(table, 'account_id', nullable=False)
        op.create_foreign_key(f'{table}_account_id_fkey', table, 'account', ['account_id'], ['id'])
        op.create_index(f'ix_{table}_account_id', table, ['account_id'])

    # booking: external_ref único por cuenta.
    op.drop_index('uq_booking_external_ref', table_name='booking')
    op.create_unique_constraint(
        'uq_booking_account_external_ref', 'booking', ['account_id', 'external_ref']
    )

    # push_device: token único por cuenta.
    op.drop_index('ix_push_device_token', table_name='push_device')
    op.create_index('ix_push_device_token', 'push_device', ['token'])
    op.create_unique_constraint(
        'uq_push_device_account_token', 'push_device', ['account_id', 'token']
    )
    op.drop_constraint('uq_push_log_kind_ref_fp', 'push_notification_log', type_='unique')
    op.create_unique_constraint(
        'uq_push_log_account_kind_ref_fp',
        'push_notification_log',
        ['account_id', 'kind', 'ref', 'fingerprint'],
    )

    op.create_unique_constraint('uq_app_preference_account', 'app_preference', ['account_id'])
    op.create_unique_constraint('uq_scan_config_account', 'scan_config', ['account_id'])
    op.create_unique_constraint(
        'uq_cm_connection_account', 'channel_manager_connection', ['account_id']
    )
    op.add_column(
        'channel_manager_connection', sa.Column('default_prop_ref', sa.String(40), nullable=True)
    )
    op.add_column(
        'channel_manager_connection', sa.Column('promo_offer_id', sa.Integer(), nullable=True)
    )

    # property: una propiedad del channel manager pertenece a una sola cuenta.
    op.add_column('property', sa.Column('provider', sa.String(20), nullable=True))
    op.execute(sa.text("UPDATE property SET provider = 'beds24' WHERE external_ref IS NOT NULL"))
    op.create_unique_constraint(
        'uq_property_provider_external_ref', 'property', ['provider', 'external_ref']
    )

    # event: dato público por ciudad. Los actuales son de la ciudad de la propiedad del host.
    first_city = bind.execute(sa.text('SELECT city FROM property ORDER BY id LIMIT 1')).scalar()
    city_key = _normalize_city(first_city)
    op.add_column(
        'event', sa.Column('city', sa.String(80), nullable=False, server_default=city_key)
    )
    op.alter_column('event', 'city', server_default=None)
    op.drop_index('ix_event_dedup_key', table_name='event')
    op.create_index('ix_event_dedup_key', 'event', ['dedup_key'])
    op.create_index('ix_event_city', 'event', ['city'])
    op.create_unique_constraint('uq_event_city_dedup', 'event', ['city', 'dedup_key'])

    # secretos: de plataforma (account_id NULL) o de una cuenta.
    names = ', '.join(f"'{n}'" for n in ACCOUNT_SECRETS)
    for table in ('secret_entry', 'secret_change_log'):
        op.add_column(table, sa.Column('account_id', sa.Integer(), nullable=True))
        op.create_foreign_key(f'{table}_account_id_fkey', table, 'account', ['account_id'], ['id'])
        op.execute(sa.text(f'UPDATE {table} SET account_id = {FIRST} WHERE name IN ({names})'))
    op.drop_index('ix_secret_entry_name', table_name='secret_entry')
    op.create_index('ix_secret_entry_name', 'secret_entry', ['name'])
    op.create_index(
        'uq_secret_platform_name',
        'secret_entry',
        ['name'],
        unique=True,
        postgresql_where=sa.text('account_id IS NULL'),
        sqlite_where=sa.text('account_id IS NULL'),
    )
    op.create_index(
        'uq_secret_account_name',
        'secret_entry',
        ['account_id', 'name'],
        unique=True,
        postgresql_where=sa.text('account_id IS NOT NULL'),
        sqlite_where=sa.text('account_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_secret_account_name', table_name='secret_entry')
    op.drop_index('uq_secret_platform_name', table_name='secret_entry')
    op.drop_index('ix_secret_entry_name', table_name='secret_entry')
    op.create_index('ix_secret_entry_name', 'secret_entry', ['name'], unique=True)
    for table in ('secret_change_log', 'secret_entry'):
        op.drop_constraint(f'{table}_account_id_fkey', table, type_='foreignkey')
        op.drop_column(table, 'account_id')

    op.drop_constraint('uq_event_city_dedup', 'event', type_='unique')
    op.drop_index('ix_event_city', table_name='event')
    op.drop_index('ix_event_dedup_key', table_name='event')
    op.create_index('ix_event_dedup_key', 'event', ['dedup_key'], unique=True)
    op.drop_column('event', 'city')

    op.drop_constraint('uq_property_provider_external_ref', 'property', type_='unique')
    op.drop_column('property', 'provider')

    op.drop_column('channel_manager_connection', 'promo_offer_id')
    op.drop_column('channel_manager_connection', 'default_prop_ref')
    op.drop_constraint('uq_cm_connection_account', 'channel_manager_connection', type_='unique')
    op.drop_constraint('uq_scan_config_account', 'scan_config', type_='unique')
    op.drop_constraint('uq_app_preference_account', 'app_preference', type_='unique')

    op.drop_constraint('uq_push_log_account_kind_ref_fp', 'push_notification_log', type_='unique')
    op.create_unique_constraint(
        'uq_push_log_kind_ref_fp', 'push_notification_log', ['kind', 'ref', 'fingerprint']
    )
    op.drop_constraint('uq_push_device_account_token', 'push_device', type_='unique')
    op.drop_index('ix_push_device_token', table_name='push_device')
    op.create_index('ix_push_device_token', 'push_device', ['token'], unique=True)

    op.drop_constraint('uq_booking_account_external_ref', 'booking', type_='unique')
    op.create_index('uq_booking_external_ref', 'booking', ['external_ref'], unique=True)

    for table in reversed(OWNED):
        op.drop_index(f'ix_{table}_account_id', table_name=table)
        op.drop_constraint(f'{table}_account_id_fkey', table, type_='foreignkey')
        op.drop_column(table, 'account_id')

    op.drop_table('account')
    op.execute(sa.text('DROP TYPE IF EXISTS accountstatus'))
