from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  -- puebla Base.metadata
from app.db import tenancy  # noqa: F401  -- filtro automático por cuenta (feature 026)
from app.db.base import Base
from app.db.tenancy import mark_platform, set_tenant
from app.models.account import FIRST_ACCOUNT_ID, Account


async def _engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Sesión async sobre SQLite en memoria (compartida vía StaticPool).

    Feature 026: existe la cuenta nº 1 y la sesión trabaja en su contexto, como la del
    host en producción; las pruebas de aislamiento usan `maker` + `two_accounts`.
    """
    engine = await _engine()
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as setup:
        mark_platform(setup)
        setup.add(Account(id=FIRST_ACCOUNT_ID, name="Mi cuenta"))
        await setup.commit()
    async with maker() as s:
        set_tenant(s, FIRST_ACCOUNT_ID)
        s.info["maker"] = maker  # para abrir sesiones de otras cuentas en las pruebas
        yield s
    await engine.dispose()


OTHER_ACCOUNT_ID = 2


@pytest_asyncio.fixture
async def other_session(session) -> AsyncGenerator[AsyncSession, None]:
    """Sesión de una SEGUNDA cuenta (B) sobre la misma base que `session` (A = cuenta 1).

    Pruebas de aislamiento (feature 026, principio VI): lo que B haga con ids de A debe
    comportarse como "no existe".
    """
    maker = session.info["maker"]
    async with maker() as setup:
        mark_platform(setup)
        setup.add(Account(id=OTHER_ACCOUNT_ID, name="Otra cuenta"))
        await setup.commit()
    async with maker() as s:
        set_tenant(s, OTHER_ACCOUNT_ID)
        s.info["maker"] = maker
        yield s
