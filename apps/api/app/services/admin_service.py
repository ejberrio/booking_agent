"""Panel del administrador de plataforma (feature 026, entrega 3).

Ve TODAS las cuentas, pero solo datos no privados: nombre, correo del dueño, estado, fechas,
si tiene channel manager y cuántas propiedades. Nunca precios, reservas ni conversaciones.
Es uno de los dos únicos módulos que usan la sesión de plataforma (test_tenancy lo vigila).
"""

from __future__ import annotations

from sqlalchemy import func, select, update

from app.core.config import settings
from app.db.tenancy import platform_session
from app.models.account import FIRST_ACCOUNT_ID, Account, AccountStatus
from app.models.auth import AppUser, Membership, UserSession
from app.models.mixins import _now
from app.models.property import Property


def _connected(account_id: int, properties: int) -> bool:
    from app.services.secret_service import get_secret

    if settings.sandbox:  # canal simulado: "conectada" = ya tiene propiedades importadas
        return properties > 0
    return bool(get_secret("beds24_refresh_token", account_id))


def _iso(dt):
    return dt.isoformat() if dt is not None else None


async def list_accounts() -> list[dict]:
    async with platform_session() as s:
        accounts = list((await s.execute(select(Account).order_by(Account.id))).scalars())
        owners = dict(
            (
                await s.execute(
                    select(Membership.account_id, AppUser.email)
                    .join(AppUser, AppUser.id == Membership.user_id)
                    .where(Membership.role == "owner")
                )
            ).all()
        )
        props = dict(
            (
                await s.execute(
                    select(Property.account_id, func.count()).group_by(Property.account_id)
                )
            ).all()
        )
    return [
        {
            "id": a.id,
            "name": a.name,
            "owner_email": owners.get(a.id),
            "status": a.status.value,
            "created_at": _iso(a.created_at),
            "last_seen_at": _iso(a.last_seen_at),
            "connected": _connected(a.id, int(props.get(a.id, 0))),
            "properties": int(props.get(a.id, 0)),
        }
        for a in accounts
    ]


async def set_status(account_id: int, *, enabled: bool, by_account_id: int) -> dict:
    if account_id == by_account_id and not enabled:
        raise ValueError("No puedes desactivar tu propia cuenta")
    if account_id == FIRST_ACCOUNT_ID and not enabled:
        raise ValueError("La cuenta principal no se puede desactivar")
    async with platform_session() as s:
        acc = await s.get(Account, account_id)
        if acc is None:
            raise LookupError("No existe esa cuenta")
        acc.status = AccountStatus.active if enabled else AccountStatus.disabled
        acc.disabled_at = None if enabled else _now()
        if not enabled:
            member_ids = select(Membership.user_id).where(Membership.account_id == account_id)
            await s.execute(
                update(UserSession)
                .where(UserSession.user_id.in_(member_ids), UserSession.revoked_at.is_(None))
                .values(revoked_at=_now())
            )
        await s.commit()
        return {"id": acc.id, "status": acc.status.value}
