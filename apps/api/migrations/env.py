import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import normalize_db_url, settings
from app.db.base import Base

# Importa los modelos para que Alembic los detecte (autogenerate).
from app import models  # noqa: E402,F401

# Normaliza la URL para asyncpg/SSL (Neon) igual que la app.
_DB_URL, _DB_CONNECT_ARGS = normalize_db_url(settings.database_url)

config = context.config
config.set_main_option("sqlalchemy.url", _DB_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(
        _DB_URL,
        poolclass=NullPool,
        connect_args=_DB_CONNECT_ARGS,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
