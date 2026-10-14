"""Privacidad de huéspedes y derechos del titular (feature 028, Ley 1581 de 2012).

- `purge_guest_names`: el nombre del huésped se borra 1 año después de la salida (el cron
  lo corre a diario por cuenta; la reserva se conserva para las estadísticas de precios).
- `export_account`: copia legible por máquina de los datos de la cuenta del contexto (derecho
  de acceso). Usa el filtro automático por cuenta, así que no puede incluir datos ajenos.
- `delete_account`: borra todos los datos de una cuenta (derecho de supresión). Recorre las
  tablas con `account_id` explícito desde una sesión de plataforma: es uno de los pocos
  módulos autorizados a usarla (`test_tenancy` lo vigila).

Nada de aquí escribe nombres de huéspedes, correos ni valores en los logs.
"""

from __future__ import annotations

import enum
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.legal import GUEST_NAME_RETENTION_DAYS, LEGAL_VERSION
from app.db.base import Base
from app.db.tenancy import platform_session
from app.models.account import FIRST_ACCOUNT_ID, Account, AccountOwned, AccountStatus
from app.models.auth import AppUser, AuthToken, Membership, TermsAcceptance, UserSession
from app.models.booking import Booking
from app.models.mixins import _now

#: Tablas de la cuenta que nunca salen en la copia: credenciales y su auditoría.
EXPORT_EXCLUDED = frozenset({"secret_entry", "secret_change_log"})


def retention_cutoff(today: date) -> date:
    return today - timedelta(days=GUEST_NAME_RETENTION_DAYS)


def keep_guest_name(check_out: date | None, today: date) -> bool:
    """¿Se puede guardar el nombre de una reserva con esta salida? (no si ya venció)."""
    return check_out is None or check_out >= retention_cutoff(today)


async def purge_guest_names(session: AsyncSession, account_id: int, today: date) -> int:
    """Vacía `guest_name` de las reservas de la cuenta con salida hace más de 1 año."""
    result = await session.execute(
        update(Booking)
        .where(
            Booking.account_id == account_id,
            Booking.check_out < retention_cutoff(today),
            Booking.guest_name.is_not(None),
        )
        .values(guest_name=None)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return result.rowcount or 0


# --------- derecho de acceso ---------


def _value(v: Any) -> Any:
    if isinstance(v, datetime | date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, enum.Enum):
        return v.value
    if isinstance(v, bytes):
        return None
    return v


def _row(obj: Any) -> dict:
    return {c.key: _value(getattr(obj, c.key)) for c in inspect(obj).mapper.column_attrs}


def _account_models() -> list[type]:
    models = [
        m.class_
        for m in Base.registry.mappers
        if issubclass(m.class_, AccountOwned) and m.class_.__tablename__ not in EXPORT_EXCLUDED
    ]
    return sorted(models, key=lambda c: c.__tablename__)


async def export_account(session: AsyncSession, user: AppUser, account: Account) -> dict:
    """Todos los datos de la cuenta del contexto (sesión con su cuenta fijada)."""
    tables: dict[str, list[dict]] = {}
    for model in _account_models():
        rows = (await session.execute(select(model).order_by(model.id))).scalars().all()
        tables[model.__tablename__] = [_row(r) for r in rows]
    acceptances = (
        await session.execute(
            select(TermsAcceptance)
            .where(TermsAcceptance.user_id == user.id)
            .order_by(TermsAcceptance.accepted_at)
        )
    ).scalars()
    return {
        "exported_at": _now().isoformat(),
        "legal_version": LEGAL_VERSION,
        "account": {"id": account.id, "name": account.name,
                    "created_at": _value(account.created_at)},
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "language": user.language,
            "email_verified": user.email_verified_at is not None,
            "signs_in_with_google": bool(user.google_sub),
            "created_at": _value(user.created_at),
        },
        "terms_acceptances": [
            {"version": a.version, "accepted_at": _value(a.accepted_at)} for a in acceptances
        ],
        "tables": tables,
    }


# --------- derecho de supresión ---------


class ProtectedAccount(Exception):
    """La cuenta principal del administrador no se borra con esta función."""


async def delete_account(account_id: int) -> None:
    """Borra todos los datos de la cuenta, su usuario y sus sesiones. La cuenta queda como
    lápida (`deleted`, sin nombre) para el registro del administrador y las invitaciones."""
    if account_id == FIRST_ACCOUNT_ID:
        raise ProtectedAccount
    async with platform_session() as s:
        user_ids = list(
            (
                await s.execute(
                    select(Membership.user_id).where(Membership.account_id == account_id)
                )
            ).scalars()
        )
        # Hijos antes que padres: el orden topológico de las FK, al revés.
        for table in reversed(Base.metadata.sorted_tables):
            if table.name != "account" and "account_id" in table.c:
                await s.execute(delete(table).where(table.c.account_id == account_id))
        if user_ids:
            for model in (UserSession, AuthToken, TermsAcceptance):
                await s.execute(delete(model).where(model.user_id.in_(user_ids)))
            await s.execute(delete(AppUser).where(AppUser.id.in_(user_ids)))
        await s.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(name="", status=AccountStatus.deleted, disabled_at=_now())
        )
        await s.commit()
    from app.services import secret_service

    secret_service.forget_account(account_id)
