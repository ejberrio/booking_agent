from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# El engine se crea de forma perezosa al primer uso; el scaffold arranca sin DB.
# La URL se normaliza para asyncpg (Neon usa ?sslmode=require, que asyncpg no acepta)
# y pool_pre_ping reconecta tras el autosuspend de Neon.
engine = create_async_engine(
    settings.normalized_database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=settings.db_connect_args,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
