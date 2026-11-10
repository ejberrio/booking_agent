"""Conexión con Beds24 desde StayLever (feature 044, #150).

- **Selección:** qué habitaciones de Beds24 sincroniza la cuenta (None = todas).
- **Salud:** estado persistente de la conexión. Cuando Beds24 deja de aceptar el token se avisa
  **una sola vez** al celular y por correo; si sigue caída a los 3 días, un recordatorio; al
  volver, el estado se limpia. Ningún aviso lleva datos de huéspedes ni el token.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.tenancy import current_account_id
from app.models.enums import ConnectionStatus
from app.models.sync import ChannelManagerConnection

log = logging.getLogger(__name__)

REMIND_AFTER = timedelta(days=3)
RECONNECT_PATH = "/onboarding"


async def get(session: AsyncSession) -> ChannelManagerConnection:
    conn = (await session.execute(select(ChannelManagerConnection))).scalar_one_or_none()
    if conn is None:
        conn = ChannelManagerConnection()
        session.add(conn)
        await session.flush()
    return conn


async def selected_rooms(session: AsyncSession) -> set[str] | None:
    conn = (await session.execute(select(ChannelManagerConnection))).scalar_one_or_none()
    if conn is None or conn.selected_rooms is None:
        return None
    return {str(r) for r in conn.selected_rooms}


async def set_selection(session: AsyncSession, room_ids: list[str] | None) -> None:
    conn = await get(session)
    conn.selected_rooms = None if room_ids is None else sorted({str(r) for r in room_ids})
    await session.flush()


def health(conn: ChannelManagerConnection | None) -> dict:
    if conn is None:
        return {"status": ConnectionStatus.unconfigured.value, "invalid_since": None, "error": None}
    return {
        "status": conn.status.value,
        "invalid_since": conn.invalid_since.isoformat() if conn.invalid_since else None,
        "error": conn.last_error,
        "last_verified_at": conn.last_verified_at.isoformat() if conn.last_verified_at else None,
    }


async def record_ok(session: AsyncSession, label: str | None = None) -> bool:
    """La conexión respondió. Devuelve True si venía caída (se restableció)."""
    conn = await get(session)
    was_invalid = conn.status == ConnectionStatus.invalid
    conn.status = ConnectionStatus.connected
    conn.last_verified_at = datetime.now(UTC)
    if label:
        conn.account_label = label[:200]
    conn.invalid_since = conn.last_error = conn.alerted_at = conn.reminded_at = None
    await session.flush()
    return was_invalid


async def record_auth_failure(session: AsyncSession, reason: str, *, now: datetime | None = None,
                              push_sender=None, email_sender=None) -> bool:
    """Beds24 rechazó el token. Marca la conexión caída y avisa la primera vez.
    Devuelve True si se envió (o intentó) el aviso."""
    now = now or datetime.now(UTC)
    conn = await get(session)
    conn.status = ConnectionStatus.invalid
    conn.last_error = (reason or "Beds24 rechazó la conexión")[:200]
    if conn.invalid_since is None:
        conn.invalid_since = now
    await session.flush()
    if conn.alerted_at is not None:
        return False
    conn.alerted_at = now
    await session.flush()
    await _alert(session, "connlost", now, push_sender=push_sender, email_sender=email_sender)
    return True


async def remind_if_due(session: AsyncSession, *, now: datetime | None = None,
                        push_sender=None, email_sender=None) -> bool:
    """Corrida diaria: un solo recordatorio si la conexión sigue caída tras 3 días."""
    now = now or datetime.now(UTC)
    conn = (await session.execute(select(ChannelManagerConnection))).scalar_one_or_none()
    if conn is None or conn.status != ConnectionStatus.invalid or conn.invalid_since is None:
        return False
    since = conn.invalid_since
    if since.tzinfo is None:  # SQLite (pruebas) no guarda la zona: es UTC
        since = since.replace(tzinfo=UTC)
    if conn.reminded_at is not None or now - since < REMIND_AFTER:
        return False
    conn.reminded_at = now
    await session.flush()
    await _alert(session, "connrem", now, push_sender=push_sender, email_sender=email_sender)
    return True


_PUSH = {
    "es": ("Se perdió la conexión con Beds24", "Reconéctala para seguir viendo reservas y aplicando precios."),
    "en": ("Connection to Beds24 lost", "Reconnect it to keep seeing bookings and applying prices."),
    "pt": ("Conexão com o Beds24 perdida", "Reconecte para continuar vendo reservas e aplicando preços."),
}


async def _alert(session: AsyncSession, kind: str, now: datetime, *, push_sender=None,
                 email_sender=None) -> None:
    """Aviso al celular y correo a los dueños. Nunca lanza (no debe tumbar la corrida)."""
    from app.email import templates
    from app.models.auth import AppUser, Membership
    from app.services import auth_service, push_service

    link = f"{settings.public_base_url.rstrip('/')}{RECONNECT_PATH}"
    try:
        lang = await push_service._lang(session)
        title, body = _PUSH.get(lang, _PUSH["es"])
        await push_service.notify(
            session, kind=f"conn-{kind}", ref="beds24", fingerprint=now.date().isoformat(),
            title=title, body=body, url=RECONNECT_PATH, pref=None, sender=push_sender,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("conexión: aviso al celular falló (%s)", type(exc).__name__)
    try:
        sender = email_sender or auth_service.get_email_sender()
        if sender is None:
            return
        account_id = current_account_id(session)
        owners = (
            await session.execute(
                select(AppUser).join(Membership, Membership.user_id == AppUser.id).where(
                    Membership.account_id == account_id, Membership.role == "owner",
                    AppUser.email_verified_at.is_not(None),
                )
            )
        ).scalars().all()
        build = templates.connection_lost if kind == "connlost" else templates.connection_reminder
        for user in owners:
            await sender.send(build(user.email, user.language, link, user.name or ""))
    except Exception as exc:  # noqa: BLE001
        log.warning("conexión: correo falló (%s)", type(exc).__name__)
