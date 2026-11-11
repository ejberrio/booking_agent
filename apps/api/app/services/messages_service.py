"""Mensajes de huéspedes (feature 045, #186): leer y responder desde StayLever.

- Los mensajes se leen EN VIVO desde Beds24 y NO se guardan en la base (sin retención extra).
  Solo se cachean 60 s en memoria por cuenta para no gastar créditos de Beds24.
- Enviar sale por el canal de la reserva (Airbnb o Booking.com vía Beds24).
- La sugerencia de la IA recibe el hilo ANONIMIZADO (sin nombre, correo, teléfono, documentos
  ni enlaces) y el anfitrión la edita: nada se envía solo. No se guardan prompt ni respuesta.
- Nunca se escriben mensajes ni nombres en logs.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tenancy import current_account_id
from app.models.booking import Booking
from app.models.enums import ChannelKind
from app.models.property import UnitType

INBOX_DAYS = 90
CACHE_SECONDS = 60
MAX_TEXT = 2000
_cache: dict[int, tuple[float, list[dict]]] = {}


class MessagesError(ValueError):
    """Mensaje legible para el anfitrión."""


def supports(adapter) -> bool:
    return hasattr(adapter, "get_messages") and hasattr(adapter, "send_message")


def forget(account_id: int | None) -> None:
    _cache.pop(account_id or 0, None)


async def _all(session: AsyncSession, adapter) -> list[dict]:
    acc = current_account_id(session) or 0
    hit = _cache.get(acc)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    msgs = await adapter.get_messages(max_age=INBOX_DAYS)
    _cache[acc] = (time.monotonic(), msgs)
    return msgs


async def _bookings(session: AsyncSession, refs: set[str]) -> dict[str, Booking]:
    if not refs:
        return {}
    rows = (await session.execute(select(Booking).where(Booking.external_ref.in_(refs)))).scalars()
    return {b.external_ref: b for b in rows}


def _short(text: str, n: int = 140) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


async def inbox(session: AsyncSession, adapter) -> list[dict]:
    """Conversaciones por reserva: no leídas primero, luego la más reciente."""
    msgs = await _all(session, adapter)
    by_booking: dict[str, list[dict]] = {}
    for m in msgs:
        if m.get("source") in ("guest", "host", "system"):
            by_booking.setdefault(str(m.get("bookingId")), []).append(m)
    bookings = await _bookings(session, set(by_booking))
    units = {u.id: u.name for u in (await session.execute(select(UnitType))).scalars()}
    out = []
    for ref, items in by_booking.items():
        b = bookings.get(ref)
        if b is None:  # reserva de otra unidad no conectada o de otra cuenta: no se muestra
            continue
        items.sort(key=lambda m: str(m.get("time") or ""))
        last = items[-1]
        out.append({
            "booking": ref, "unit": units.get(b.unit_type_id), "channel": b.channel_kind.value,
            "check_in": b.check_in.isoformat(), "check_out": b.check_out.isoformat(),
            "guest_name": b.guest_name,
            "unread": sum(1 for m in items if m.get("source") == "guest" and not m.get("read")),
            "last_time": last.get("time"), "last_source": last.get("source"),
            "last_text": _short(str(last.get("message") or "")),
        })
    unread_first = [c for c in out if c["unread"]]
    rest = [c for c in out if not c["unread"]]
    unread_first.sort(key=lambda c: str(c["last_time"] or ""), reverse=True)
    rest.sort(key=lambda c: str(c["last_time"] or ""), reverse=True)
    return unread_first + rest


async def unread_count(session: AsyncSession, adapter) -> int:
    return sum(c["unread"] for c in await inbox(session, adapter))


async def _booking_or_404(session: AsyncSession, ref: str) -> Booking:
    b = (await session.execute(select(Booking).where(Booking.external_ref == str(ref)))).scalar_one_or_none()
    if b is None:
        raise LookupError("No existe esa reserva en tu cuenta")
    return b


async def thread(session: AsyncSession, adapter, ref: str) -> dict:
    b = await _booking_or_404(session, ref)
    msgs = await adapter.get_messages(booking_ids=[ref], max_age=999)
    msgs.sort(key=lambda m: str(m.get("time") or ""))
    if any(m.get("source") == "guest" and not m.get("read") for m in msgs):
        try:
            await adapter.mark_messages_read(ref)
        except Exception:  # noqa: BLE001 — marcar leído no debe impedir leer
            pass
        forget(current_account_id(session))
    unit = await session.get(UnitType, b.unit_type_id)
    return {
        "booking": ref, "unit": unit.name if unit else None, "channel": b.channel_kind.value,
        "check_in": b.check_in.isoformat(), "check_out": b.check_out.isoformat(),
        "guest_name": b.guest_name, "can_reply": b.channel_kind in (ChannelKind.airbnb, ChannelKind.booking),
        "messages": [
            {"id": m.get("id"), "source": m.get("source"), "time": m.get("time"),
             "text": str(m.get("message") or "")}
            for m in msgs if m.get("source") in ("guest", "host", "system", "internalNote")
        ],
    }


async def send(session: AsyncSession, adapter, ref: str, text: str) -> None:
    b = await _booking_or_404(session, ref)
    text = (text or "").strip()
    if not text:
        raise MessagesError("El mensaje está vacío.")
    if len(text) > MAX_TEXT:
        raise MessagesError(f"El mensaje supera {MAX_TEXT} caracteres.")
    if b.channel_kind not in (ChannelKind.airbnb, ChannelKind.booking):
        raise MessagesError("Solo se puede responder reservas de Airbnb o Booking.com desde StayLever.")
    await adapter.send_message(ref, text)
    forget(current_account_id(session))


# --------- sugerencia de la IA (sin datos personales) ---------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_URL = re.compile(r"(https?://|www\.)\S+", re.I)
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)")
_LONGNUM = re.compile(r"\b\d{6,}\b")


def redact(text: str, names: list[str] | None = None) -> str:
    """Quita datos personales antes de enviar a la IA: nombre(s) del huésped, correos, enlaces,
    teléfonos y números largos (documentos, códigos)."""
    out = _EMAIL.sub("[correo]", text or "")
    out = _URL.sub("[enlace]", out)
    out = _PHONE.sub("[teléfono]", out)
    out = _LONGNUM.sub("[número]", out)
    for name in names or []:
        for part in {p for p in re.split(r"\s+", name or "") if len(p) >= 3}:
            out = re.sub(rf"\b{re.escape(part)}\b", "[huésped]", out, flags=re.I)
    return out


_SYSTEM = (
    "Eres el asistente de un anfitrión de alquiler vacacional en Colombia. Redacta UNA respuesta "
    "breve, cordial y concreta al último mensaje del huésped, en el MISMO idioma del huésped. "
    "No inventes datos que no estén en el contexto (horarios, claves, direcciones, precios): si "
    "faltan, deja un espacio entre corchetes para que el anfitrión lo complete, p. ej. [hora de "
    "check-in]. No incluyas saludos con nombres. Responde solo con el texto del mensaje."
)


@dataclass
class Suggestion:
    text: str


async def suggest(session: AsyncSession, adapter, llm, ref: str, *, model: str) -> Suggestion:
    b = await _booking_or_404(session, ref)
    data = await thread(session, adapter, ref)
    names = [b.guest_name] if b.guest_name else []
    convo = [m for m in data["messages"] if m["source"] in ("guest", "host")][-10:]
    if not any(m["source"] == "guest" for m in convo):
        raise MessagesError("No hay mensajes del huésped para responder.")
    nights = (b.check_out - b.check_in).days
    context = (
        f"Reserva por {b.channel_kind.value}: llegada {b.check_in.isoformat()}, salida "
        f"{b.check_out.isoformat()} ({nights} noche(s)), alojamiento: {data['unit'] or 'apartamento'}."
    )
    lines = [f"{'Huésped' if m['source'] == 'guest' else 'Anfitrión'}: {redact(m['text'], names)}"
             for m in convo]
    resp = await llm.chat(
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": context + "\n\nConversación:\n" + "\n".join(lines)}],
        tools=[], model=model,
    )
    text = redact((resp.content or "").strip(), names)
    if not text:
        raise MessagesError("La IA no devolvió una sugerencia. Intenta de nuevo.")
    return Suggestion(text=text[:MAX_TEXT])


# --------- aviso al celular (feature 045, FR-006) ---------

_PUSH = {
    "es": ("Mensaje nuevo de un huésped", "{channel}, {dates}. Ábrelo en StayLever para responder."),
    "en": ("New message from a guest", "{channel}, {dates}. Open StayLever to reply."),
    "pt": ("Nova mensagem de um hóspede", "{channel}, {dates}. Abra o StayLever para responder."),
}
_CHANNEL = {"booking": "Booking.com", "airbnb": "Airbnb", "direct": "Directa"}


async def notify_new(session: AsyncSession, booking_ref: str | None, message_ids) -> int:
    """Un aviso por mensaje nuevo (deduplicado por id). Nunca lanza."""
    from app.services import push_service

    if not booking_ref or not message_ids:
        return 0
    forget(current_account_id(session))
    try:
        b = (await session.execute(select(Booking).where(Booking.external_ref == str(booking_ref)))).scalar_one_or_none()
        lang = await push_service._lang(session)
        title, body = _PUSH.get(lang, _PUSH["es"])
        dates = push_service._range(b.check_in, b.check_out, lang) if b else ""
        channel = _CHANNEL.get(b.channel_kind.value, "") if b else ""
        sent = 0
        for mid in message_ids:
            sent += await push_service.notify(
                session, kind="guest-msg", ref=str(booking_ref), fingerprint=str(mid),
                title=title, body=body.format(channel=channel, dates=dates).strip(", "),
                url=f"/messages?booking={booking_ref}", pref=push_service.PREF_BOOKINGS,
            )
        return sent
    except Exception:  # noqa: BLE001 — el aviso nunca rompe el webhook
        return 0
