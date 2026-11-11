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


# --------- de «sin conexión» a Beds24 (feature 044, entrega 2) ---------


class SwitchError(ValueError):
    """Asociación inválida (mensaje legible para el anfitrión)."""


def beds24_adapter(session: AsyncSession):
    """Adaptador de Beds24 de la cuenta aunque esté en modo sin conexión (para el asistente).
    En el ambiente de pruebas, el simulado."""
    from app.channels.beds24_v2 import Beds24V2Adapter
    from app.channels.factory import REFRESH_TOKEN
    from app.channels.simulated import SimulatedChannelAdapter
    from app.services.secret_service import get_secret

    if settings.sandbox:
        return SimulatedChannelAdapter(session)
    return Beds24V2Adapter(refresh_token=get_secret(REFRESH_TOKEN, current_account_id(session)),
                           base_url=settings.beds24_v2_base_url)


async def manual_units(session: AsyncSession) -> list[dict]:
    from app.models.property import Property, UnitType
    from app.services.manual_service import PROVIDER

    rows = (
        await session.execute(
            select(UnitType, Property).join(Property, Property.id == UnitType.property_id)
            .where(Property.provider == PROVIDER).order_by(UnitType.id)
        )
    ).all()
    return [{"id": u.id, "name": u.name, "city": p.city} for u, p in rows]


async def switch_from_manual(session: AsyncSession, links: dict[int, str], remote_props: list) -> dict:
    """Asocia cada apartamento manual con su habitación de Beds24 y pasa la cuenta a conectada.

    Se conserva la MISMA unidad (id), así que su historial sigue intacto: precios aplicados,
    sugerencias, notas, rentabilidad y finanzas. Los enlaces iCal quedan guardados pero sin
    uso (la corrida diaria solo lee iCal en modo sin conexión). Las reservas duplicadas de
    iCal se quitan en la siguiente importación (`sync_service._drop_ical_duplicates`).
    """
    from app.channels.factory import set_channel_mode
    from app.db.cross_account import property_taken_elsewhere
    from app.models.account import Account
    from app.models.property import Property, UnitType
    from app.services.manual_service import PROVIDER

    room_prop = {str(r.external_id): p for p in remote_props for r in p.rooms}
    if len(set(links.values())) != len(links):
        raise SwitchError("Cada habitación de Beds24 solo puede asociarse con un apartamento.")
    targets: dict[str, Property] = {}
    linked = 0
    for unit_id, room_id in links.items():
        unit = await session.get(UnitType, int(unit_id))
        if unit is None:
            raise SwitchError("Ese apartamento no existe en tu cuenta.")
        prop = await session.get(Property, unit.property_id)
        if prop is None or prop.provider != PROVIDER:
            raise SwitchError(f"«{unit.name}» no es un apartamento sin conexión.")
        rp = room_prop.get(str(room_id))
        if rp is None:
            raise SwitchError("Esa habitación no está en tu cuenta de Beds24.")
        ext = str(rp.external_id)
        if await property_taken_elsewhere(session, "beds24", ext):
            raise SwitchError(f"«{rp.name}» ya está conectada a otra cuenta de StayLever.")
        target = targets.get(ext) or (
            await session.execute(select(Property).where(Property.provider == "beds24",
                                                         Property.external_ref == ext))
        ).scalar_one_or_none()
        if target is None:  # el apartamento manual se convierte en la propiedad de Beds24
            prop.provider, prop.external_ref, prop.name = "beds24", ext, rp.name[:200]
            prop.currency = rp.currency or prop.currency
            target = prop
        targets[ext] = target
        unit.property_id = target.id
        unit.external_ref = str(room_id)
        linked += 1
    pending = [u for u in await manual_units(session) if u["id"] not in {int(k) for k in links}]
    if pending:
        raise SwitchError("Asocia cada apartamento sin conexión con su habitación de Beds24 "
                          f"(falta: {', '.join(u['name'] for u in pending)}).")
    acc = await session.get(Account, current_account_id(session))
    acc.channel_mode = "connected"
    set_channel_mode(session, "connected")
    await session.flush()
    return {"linked": linked}
