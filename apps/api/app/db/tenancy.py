"""Aislamiento por cuenta en el ORM (feature 026, principio VI).

Cada sesión de base de datos lleva su cuenta en `session.info["account_id"]`:

- `do_orm_execute` añade `WHERE account_id = <cuenta>` a todo SELECT/UPDATE/DELETE del
  ORM sobre tablas `AccountOwned` (incluye `session.get`, relaciones y alias).
- `before_flush` rellena `account_id` en filas nuevas y rechaza filas de otra cuenta.
- **Falla cerrado**: sin cuenta en la sesión, tocar una tabla `AccountOwned` lanza
  `TenantContextMissing` (salvo una sesión de plataforma explícita).

La sesión de plataforma (`session.info["platform"] = True`) ve todas las cuentas y solo
la usan el panel de administrador y el recorrido del cron (prueba en test_tenancy).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from app.models.account import AccountOwned

ACCOUNT_KEY = "account_id"
USER_KEY = "user_id"
PLATFORM_KEY = "platform"


class TenantContextMissing(RuntimeError):
    """Se tocó una tabla de una cuenta sin cuenta en el contexto (bug: falla cerrado)."""


class CrossTenantWrite(RuntimeError):
    """Se intentó escribir una fila de otra cuenta."""


def set_tenant(session: AsyncSession | Session, account_id: int, user_id: int | None = None) -> None:
    """Fija la cuenta (y el usuario) de la sesión. Una sesión no cambia de cuenta."""
    info = session.info
    current = info.get(ACCOUNT_KEY)
    if current is not None and current != account_id:
        raise CrossTenantWrite("la sesión ya pertenece a otra cuenta")
    info[ACCOUNT_KEY] = account_id
    info[USER_KEY] = user_id
    info.pop(PLATFORM_KEY, None)


def current_account_id(session: AsyncSession | Session) -> int | None:
    return session.info.get(ACCOUNT_KEY)


def current_user_id(session: AsyncSession | Session) -> int | None:
    return session.info.get(USER_KEY)


def mark_platform(session: AsyncSession | Session) -> None:
    """Sesión de plataforma: ve todas las cuentas. Solo admin_service y el cron."""
    if session.info.get(ACCOUNT_KEY) is not None:
        raise CrossTenantWrite("una sesión de cuenta no puede volverse de plataforma")
    session.info[PLATFORM_KEY] = True


def _is_owned(mapper) -> bool:
    return mapper is not None and issubclass(mapper.class_, AccountOwned)


@event.listens_for(Session, "do_orm_execute")
def _scope_to_account(state: ORMExecuteState) -> None:
    if not (state.is_select or state.is_update or state.is_delete):
        return
    if state.is_column_load:
        return  # carga diferida de columnas de una fila ya filtrada
    info = state.session.info
    if info.get(PLATFORM_KEY):
        return
    account_id = info.get(ACCOUNT_KEY)
    if account_id is None:
        if any(_is_owned(m) for m in state.all_mappers):
            raise TenantContextMissing(
                "consulta sobre datos de una cuenta sin cuenta en el contexto"
            )
        return
    state.statement = state.statement.options(
        with_loader_criteria(
            AccountOwned,
            lambda cls: cls.account_id == account_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _assign_account(session: Session, _flush_context, _instances) -> None:
    info = session.info
    account_id = info.get(ACCOUNT_KEY)
    platform = info.get(PLATFORM_KEY, False)
    for obj in session.new:
        if not isinstance(obj, AccountOwned):
            continue
        if obj.account_id is None:
            if account_id is None:
                raise TenantContextMissing(
                    f"{type(obj).__name__} nuevo sin cuenta en el contexto"
                )
            obj.account_id = account_id
        elif account_id is not None and obj.account_id != account_id:
            raise CrossTenantWrite(f"{type(obj).__name__} de otra cuenta")
        elif account_id is None and not platform:
            raise TenantContextMissing(f"{type(obj).__name__} nuevo sin contexto")
    for obj in session.dirty:
        if not isinstance(obj, AccountOwned):
            continue
        hist = inspect(obj).attrs.account_id.history
        if hist.has_changes() and hist.deleted and hist.deleted[0] is not None:
            raise CrossTenantWrite("no se puede mover una fila a otra cuenta")


@asynccontextmanager
async def tenant_session(account_id: int, user_id: int | None = None) -> AsyncIterator[AsyncSession]:
    """Sesión nueva con el contexto de una cuenta (tareas programadas, webhooks)."""
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        set_tenant(session, account_id, user_id)
        yield session


@asynccontextmanager
async def platform_session() -> AsyncIterator[AsyncSession]:
    """Sesión que ve todas las cuentas. SOLO admin_service y el recorrido del cron."""
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        mark_platform(session)
        yield session
