"""Avisos al celular (feature 025).

Registra los teléfonos con la app instalada y envía avisos de reservas (nueva,
modificada, cancelada) y de sugerencias nuevas. Cada cambio se avisa UNA vez
(registro único tipo+referencia+huella). Sin credenciales configuradas no envía
nada y nunca rompe la sincronización ni el escaneo. Los avisos no llevan datos
personales del huésped y nunca se registra el token del teléfono.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.cross_account import release_push_token
from app.models.mixins import _now
from app.models.preference import AppPreference
from app.models.push import PushDevice, PushNotificationLog
from app.push.base import PushMessage, PushSender
from app.services import secret_service

log = logging.getLogger(__name__)

SECRET = "fcm_service_account"
PREF_BOOKINGS = "bookings"
PREF_SUGGESTIONS = "suggestions"

_TEXTS: dict[str, dict[str, str]] = {
    "es": {
        "new": "Nueva reserva",
        "modified": "Reserva modificada",
        "cancelled": "Reserva cancelada",
        "suggestions_title": "Sugerencias de precio",
        "suggestions_one": "1 sugerencia nueva para revisar",
        "suggestions_many": "{n} sugerencias nuevas para revisar",
        "test_title": "StayLever",
        "test_body": "Aviso de prueba: los avisos funcionan ✅",
        "direct": "Directa",
        "months": "ene feb mar abr may jun jul ago sep oct nov dic",
    },
    "en": {
        "new": "New booking",
        "modified": "Booking changed",
        "cancelled": "Booking canceled",
        "suggestions_title": "Price suggestions",
        "suggestions_one": "1 new suggestion to review",
        "suggestions_many": "{n} new suggestions to review",
        "test_title": "StayLever",
        "test_body": "Test notification: notifications work ✅",
        "direct": "Direct",
        "months": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec",
    },
    "pt": {
        "new": "Nova reserva",
        "modified": "Reserva alterada",
        "cancelled": "Reserva cancelada",
        "suggestions_title": "Sugestões de preço",
        "suggestions_one": "1 sugestão nova para revisar",
        "suggestions_many": "{n} sugestões novas para revisar",
        "test_title": "StayLever",
        "test_body": "Aviso de teste: os avisos funcionam ✅",
        "direct": "Direta",
        "months": "jan fev mar abr mai jun jul ago set out nov dez",
    },
}
_CHANNELS = {"booking": "Booking.com", "airbnb": "Airbnb"}


# --------- envío (inyectable en tests) ---------


def get_sender() -> PushSender | None:
    """Adaptador vigente o None si no hay credencial válida."""
    from app.push.fcm import FcmConfigError, FcmSender

    try:
        return FcmSender(secret_service.get_secret(SECRET))
    except FcmConfigError:
        return None


def configured() -> bool:
    from app.push.fcm import FcmConfigError, parse_service_account

    try:
        parse_service_account(secret_service.get_secret(SECRET))
        return True
    except FcmConfigError:
        return False


# --------- teléfonos ---------


async def register_device(
    session: AsyncSession,
    *,
    token: str,
    platform: str = "android",
    model: str | None = None,
    app_version: str | None = None,
) -> PushDevice:
    token = token.strip()
    if not token:
        raise ValueError("token vacío")
    # Feature 026: el teléfono deja de recibir avisos de otras cuentas.
    await release_push_token(session, token)
    dev = (
        await session.execute(select(PushDevice).where(PushDevice.token == token))
    ).scalar_one_or_none()
    if dev is None:
        dev = PushDevice(token=token)
        session.add(dev)
    dev.platform = (platform or "android")[:16]
    dev.model = (model or None) and model[:120]
    dev.app_version = (app_version or None) and app_version[:32]
    dev.enabled = True
    dev.last_error = None
    dev.last_seen_at = _now()
    await session.flush()
    return dev


async def list_devices(session: AsyncSession) -> list[PushDevice]:
    return list(
        (
            await session.execute(select(PushDevice).order_by(PushDevice.last_seen_at.desc()))
        ).scalars()
    )


async def update_device(
    session: AsyncSession,
    device_id: int,
    *,
    notify_bookings: bool | None = None,
    notify_suggestions: bool | None = None,
) -> PushDevice:
    dev = await session.get(PushDevice, device_id)
    if dev is None:
        raise LookupError(f"No existe el teléfono {device_id}")
    if notify_bookings is not None:
        dev.notify_bookings = notify_bookings
    if notify_suggestions is not None:
        dev.notify_suggestions = notify_suggestions
    await session.flush()
    return dev


async def delete_device(session: AsyncSession, device_id: int) -> None:
    dev = await session.get(PushDevice, device_id)
    if dev is None:
        raise LookupError(f"No existe el teléfono {device_id}")
    await session.delete(dev)
    await session.flush()


# --------- textos ---------


async def _lang(session: AsyncSession) -> str:
    pref = (await session.execute(select(AppPreference).limit(1))).scalars().first()
    return pref.language if pref and pref.language in _TEXTS else "es"


def _range(check_in: date, check_out: date, lang: str) -> str:
    months = _TEXTS[lang]["months"].split()
    a = f"{check_in.day} {months[check_in.month - 1]}"
    b = f"{check_out.day} {months[check_out.month - 1]}"
    if lang == "en":
        a = f"{months[check_in.month - 1]} {check_in.day}"
        b = f"{months[check_out.month - 1]} {check_out.day}"
    return f"{a} – {b}"


# --------- envío con deduplicación ---------


async def notify(
    session: AsyncSession,
    *,
    kind: str,
    ref: str,
    fingerprint: str,
    title: str,
    body: str,
    url: str,
    pref: str | None,
    sender: PushSender | None = None,
) -> int:
    """Envía a los teléfonos activos (con la preferencia `pref`) una sola vez por cambio.
    Devuelve a cuántos se envió. Nunca lanza."""
    exists = (
        await session.execute(
            select(PushNotificationLog.id).where(
                PushNotificationLog.kind == kind,
                PushNotificationLog.ref == ref,
                PushNotificationLog.fingerprint == fingerprint,
            )
        )
    ).first()
    if exists:
        return 0
    q = select(PushDevice).where(PushDevice.enabled.is_(True))
    if pref == PREF_BOOKINGS:
        q = q.where(PushDevice.notify_bookings.is_(True))
    elif pref == PREF_SUGGESTIONS:
        q = q.where(PushDevice.notify_suggestions.is_(True))
    devices = list((await session.execute(q)).scalars())
    if not devices:
        return 0
    own_sender = sender is None
    sender = sender or get_sender()
    if sender is None:
        return 0  # sin credenciales: no se envía (ni se marca como enviado)
    sent = 0
    try:
        for dev in devices:
            res = await sender.send(PushMessage(dev.token, title, body, {"url": url}))
            if res.status == "ok":
                sent += 1
                dev.last_error = None
            elif res.status == "invalid_token":
                dev.enabled = False
                dev.last_error = res.detail
            else:
                dev.last_error = (res.detail or "error")[:300]
                log.warning("push: envío fallido (%s)", res.detail)
    finally:
        if own_sender:
            await sender.aclose()
    session.add(PushNotificationLog(kind=kind, ref=ref, fingerprint=fingerprint, sent=sent))
    await session.flush()
    return sent


async def notify_booking_events(
    session: AsyncSession, events: list, *, sender: PushSender | None = None
) -> int:
    """Avisos de reservas (feature 025). Tolerante a fallos: nunca rompe la sync."""
    if not events:
        return 0
    total = 0
    try:
        lang = await _lang(session)
        t = _TEXTS[lang]
        for ev in events:
            channel = _CHANNELS.get(ev.channel, t["direct"])
            total += await notify(
                session,
                kind=f"booking_{ev.kind}",
                ref=ev.ref,
                fingerprint=f"{ev.status}:{ev.check_in.isoformat()}:{ev.check_out.isoformat()}",
                title=t[ev.kind],
                body=f"{channel} · {_range(ev.check_in, ev.check_out, lang)}",
                url=f"/calendar?month={ev.check_in:%Y-%m}",
                pref=PREF_BOOKINGS,
                sender=sender,
            )
    except Exception as exc:  # noqa: BLE001 — solo el tipo; los avisos nunca rompen la sync
        log.warning("push: avisos de reservas omitidos (%s)", type(exc).__name__)
    return total


async def notify_suggestions(
    session: AsyncSession, run_id: int, count: int, *, sender: PushSender | None = None
) -> int:
    if count <= 0:
        return 0
    try:
        t = _TEXTS[await _lang(session)]
        body = t["suggestions_one"] if count == 1 else t["suggestions_many"].format(n=count)
        return await notify(
            session,
            kind="suggestions",
            ref=str(run_id),
            fingerprint=str(count),
            title=t["suggestions_title"],
            body=body,
            url="/suggestions",
            pref=PREF_SUGGESTIONS,
            sender=sender,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("push: aviso de sugerencias omitido (%s)", type(exc).__name__)
        return 0


async def send_test(session: AsyncSession, *, sender: PushSender | None = None) -> dict:
    if sender is None and not configured():
        return {"sent": 0, "failed": 0, "configured": False}
    t = _TEXTS[await _lang(session)]
    devices = [d for d in await list_devices(session) if d.enabled]
    own = sender is None
    sender = sender or get_sender()
    if sender is None:
        return {"sent": 0, "failed": 0, "configured": False}
    sent = failed = 0
    try:
        for dev in devices:
            res = await sender.send(PushMessage(dev.token, t["test_title"], t["test_body"], {"url": "/settings"}))
            if res.status == "ok":
                sent += 1
                dev.last_error = None
            else:
                failed += 1
                dev.last_error = (res.detail or "error")[:300]
                if res.status == "invalid_token":
                    dev.enabled = False
    finally:
        if own:
            await sender.aclose()
    await session.flush()
    return {"sent": sent, "failed": failed, "configured": True}
