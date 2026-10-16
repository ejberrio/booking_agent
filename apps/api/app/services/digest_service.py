"""Resumen semanal por correo (feature 030): el gancho de retención del modo sin conexión.

Cada lunes (hora de Colombia), después del escaneo de la cuenta, el dueño recibe:
- las noches de los próximos 14 días con sugerencia pendiente (precio actual → sugerido) y,
  sin conexión, los enlaces para aplicarlo en cada plataforma;
- los eventos nuevos de la semana en su ciudad.

Si no hay nada que contar no se envía. Una vez por cuenta y semana (`account.digest_sent_on`).
Se apaga desde el enlace del correo (firmado) o en Ajustes (`app_user.weekly_digest`).
Nunca lleva nombres de huéspedes.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.account import Account
from app.models.auth import AppUser, Membership
from app.models.enums import Relevance, SuggestionStatus
from app.models.market import Event, PriceSuggestion
from app.models.mixins import _now
from app.services import event_service, intelligence_service, pricing_service

WEEKDAY = 0  # lunes
NEXT_DAYS = 14
MAX_NIGHTS = 8
MAX_EVENTS = 5
_REL = {Relevance.high: 0, Relevance.medium: 1, Relevance.low: 2}


def unsubscribe_token(user_id: int) -> str:
    msg = f"digest-off:{user_id}".encode()
    return hmac.new(settings.secret_key.encode(), msg, hashlib.sha256).hexdigest()[:32]


def unsubscribe_link(user_id: int) -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/unsubscribe?u={user_id}&t={unsubscribe_token(user_id)}"


async def unsubscribe(session: AsyncSession, user_id: int, token: str) -> bool:
    if not hmac.compare_digest(unsubscribe_token(user_id), (token or "")[:64]):
        return False
    user = await session.get(AppUser, user_id)
    if user is None:
        return False
    user.weekly_digest = False
    await session.commit()
    return True


async def build(session: AsyncSession, account_id: int, today: date) -> dict | None:
    """Contenido del resumen para la cuenta del contexto, o None si no hay nada que contar."""
    from app.services import manual_service

    rows = (
        await session.execute(
            select(PriceSuggestion)
            .where(
                PriceSuggestion.status == SuggestionStatus.proposed,
                PriceSuggestion.date_from >= today,
                PriceSuggestion.date_from <= today + timedelta(days=NEXT_DAYS),
            )
            .order_by(PriceSuggestion.date_from)
            .limit(MAX_NIGHTS)
        )
    ).scalars().all()
    nights = []
    for s in rows:
        current = (
            await pricing_service.get_price(session, s.unit_type_id, s.date_from)
            if s.unit_type_id else None
        )
        reason = ""
        factors = (s.rationale or {}).get("factors") or []
        if factors:
            reason = (factors[0].get("event") or {}).get("name") or factors[0].get("label") or ""
        nights.append({
            "date_from": s.date_from.isoformat(),
            "date_to": s.date_to.isoformat(),
            "current": str(current) if current is not None else None,
            "suggested": str(s.suggested_price),
            "reason": reason[:120],
        })
    from app.domain import municipalities

    keys = municipalities.area_keys(await intelligence_service.property_city(session))
    week_ago = _now() - timedelta(days=7)
    new_events = event_service.unique_events(sorted(
        (
            await session.execute(
                select(Event).where(
                    Event.city.in_(keys), Event.created_at >= week_ago, Event.start_date >= today
                )
            )
        ).scalars().all(),
        key=lambda e: (_REL.get(e.relevance, 3), e.start_date),
    ))[:MAX_EVENTS]
    if not nights and not new_events:
        return None
    links = []
    for apt in await manual_service.overview(session):
        links += [c for c in apt["channels"] if c.get("calendar_url")]
    acc = await session.get(Account, account_id)
    return {
        "account": acc.name if acc else "",
        "manual": bool(acc and acc.channel_mode == "manual"),
        "nights": nights,
        "events": [
            {"name": e.name, "start_date": e.start_date.isoformat(), "relevance": e.relevance.value}
            for e in new_events
        ],
        "links": [{"channel": c["channel"], "url": c["calendar_url"]} for c in links],
    }


async def send_weekly(
    session: AsyncSession, account_id: int, today: date, sender, *, force: bool = False
) -> int:
    """Envía el resumen a los dueños de la cuenta que lo tienen activo. Devuelve cuántos."""
    from app.email import templates

    if sender is None or (not force and today.weekday() != WEEKDAY):
        return 0
    acc = await session.get(Account, account_id)
    if acc is None or acc.digest_sent_on == today:
        return 0
    data = await build(session, account_id, today)
    if data is None:
        return 0
    owners = (
        await session.execute(
            select(AppUser)
            .join(Membership, Membership.user_id == AppUser.id)
            .where(
                Membership.account_id == account_id,
                Membership.role == "owner",
                AppUser.weekly_digest.is_(True),
                AppUser.email_verified_at.is_not(None),
            )
        )
    ).scalars().all()
    if not owners:
        return 0
    acc.digest_sent_on = today
    await session.commit()
    link = f"{settings.public_base_url.rstrip('/')}/suggestions"
    for user in owners:
        await sender.send(
            templates.weekly_digest(user.email, user.language, data, link,
                                    unsubscribe_link(user.id))
        )
    return len(owners)
