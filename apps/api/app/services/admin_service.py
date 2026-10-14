"""Panel del administrador de plataforma (feature 026, entrega 3).

Ve TODAS las cuentas, pero solo datos no privados: nombre, correo del dueño, estado, fechas,
si tiene channel manager y cuántas propiedades. Nunca precios, reservas ni conversaciones.
Es uno de los dos únicos módulos que usan la sesión de plataforma (test_tenancy lo vigila).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

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
        if acc.status == AccountStatus.deleted:
            raise ValueError("Esa cuenta fue eliminada por su dueño")
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


# --------- uso de IA (feature 027) ---------


async def usage(month: date) -> dict:
    """Uso y costo de IA por cuenta en el mes (sin contenido: solo contadores)."""
    from app.models.usage import AIUsage
    from app.services.usage_service import CHAT_MESSAGE, SEARCH, month_start, next_month

    start, end = month_start(month), next_month(month)
    async with platform_session() as s:
        accounts = list((await s.execute(select(Account).order_by(Account.id))).scalars())
        rows = (
            await s.execute(
                select(
                    AIUsage.account_id,
                    AIUsage.kind,
                    func.sum(AIUsage.calls),
                    func.sum(AIUsage.input_tokens),
                    func.sum(AIUsage.output_tokens),
                    func.sum(AIUsage.cost_usd),
                    func.sum(AIUsage.unpriced),
                )
                .where(AIUsage.day >= start, AIUsage.day < end)
                .group_by(AIUsage.account_id, AIUsage.kind)
            )
        ).all()
    per: dict[int, dict] = {}
    for acc_id, kind, calls, tin, tout, cost, unpriced in rows:
        d = per.setdefault(acc_id, {"chat_messages": 0, "llm_calls": 0, "input_tokens": 0,
                                    "output_tokens": 0, "searches": 0, "cost": Decimal("0"),
                                    "unpriced": 0})
        if kind == CHAT_MESSAGE:
            d["chat_messages"] += int(calls or 0)
        elif kind == SEARCH:
            d["searches"] += int(calls or 0)
        else:
            d["llm_calls"] += int(calls or 0)
        d["input_tokens"] += int(tin or 0)
        d["output_tokens"] += int(tout or 0)
        d["cost"] += Decimal(cost or 0)
        d["unpriced"] += int(unpriced or 0)
    out = []
    total = Decimal("0")
    for a in accounts:
        d = per.get(a.id)
        if d is None and a.status == AccountStatus.deleted:
            continue
        d = d or {"chat_messages": 0, "llm_calls": 0, "input_tokens": 0, "output_tokens": 0,
                  "searches": 0, "cost": Decimal("0"), "unpriced": 0}
        total += d["cost"]
        out.append({
            "id": a.id,
            "name": a.name,
            "status": a.status.value,
            "chat_messages": d["chat_messages"],
            "llm_calls": d["llm_calls"],
            "input_tokens": d["input_tokens"],
            "output_tokens": d["output_tokens"],
            "searches": d["searches"],
            "cost_usd": round(float(d["cost"]), 4),
            "unpriced": d["unpriced"],
            "chat_limit_month": a.chat_limit_month if a.chat_limit_month is not None
            else settings.ai_chat_limit_month,
            "search_limit_day": a.search_limit_day if a.search_limit_day is not None
            else settings.ai_search_limit_day,
            "custom_limits": a.chat_limit_month is not None or a.search_limit_day is not None,
        })
    return {"month": start.isoformat()[:7], "accounts": out, "total_cost_usd": round(float(total), 4)}


_UNSET = object()


async def set_limits(account_id: int, *, chat_limit_month=_UNSET, search_limit_day=_UNSET) -> dict:
    """None = volver al valor por defecto de la plataforma."""
    async with platform_session() as s:
        acc = await s.get(Account, account_id)
        if acc is None:
            raise LookupError("No existe esa cuenta")
        if acc.status == AccountStatus.deleted:
            raise ValueError("Esa cuenta fue eliminada por su dueño")
        if chat_limit_month is not _UNSET:
            acc.chat_limit_month = chat_limit_month
        if search_limit_day is not _UNSET:
            acc.search_limit_day = search_limit_day
        await s.commit()
        return {"id": acc.id, "chat_limit_month": acc.chat_limit_month,
                "search_limit_day": acc.search_limit_day}
