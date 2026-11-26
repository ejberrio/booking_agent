"""Registro de huéspedes para la TRA (MinCIT) y SIRE (Migración). Feature 046, #167.

- El huésped llena sus datos por un enlace público por reserva (`/checkin/{token}`); el
  anfitrión los revisa y pulsa «Enviar TRA». Nada se envía solo.
- Los datos personales se guardan CIFRADOS con una clave derivada por cuenta y se borran 1 año
  después de la salida (028). Nunca van a logs, a la IA ni a los avisos; el administrador de
  plataforma no los ve.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.tenancy import current_account_id, current_user_id
from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.mixins import _now
from app.models.property import UnitType
from app.models.registration import (
    PENDING,
    SUBMITTED,
    TRA_ERROR,
    TRA_PARTIAL,
    TRA_SENT,
    GuestRegistration,
    RegistrationSettings,
)
from app.registration.tra import TraError

TOKEN_SECRET = "mincit_tra_token"
MAX_COMPANIONS = 15
WINDOW_PAST, WINDOW_FUTURE = 7, 30

# Documentos (código interno → texto de la TRA). R.C solo para acompañantes (menores).
DOC_TYPES = {"CC": "C.C", "CE": "C.E", "TI": "T.I", "PA": "Pasaporte", "RC": "R.C"}
MAIN_DOC_TYPES = {"CC", "CE", "TI", "PA"}
# Motivo del viaje (catálogo del formulario web del MinCIT, Res. 409).
MOTIVES = {
    "business": "Negocios y motivos profesionales",
    "leisure": "Vacaciones, recreo y ocio",
    "family": "Visitas a familiares y a amigos",
    "education": "Educación y formación",
    "health": "Salud y atención médica",
    "religion": "Religión/ peregrinaciones",
    "shopping": "Compras",
    "transit": "Tránsito",
    "other": "Otros motivos",
}
ACCOMMODATIONS = ("Apartamento", "Casa", "Finca", "Cabaña", "Suite", "Sencilla", "Doble", "Múltiple")


class RegistrationError(ValueError):
    """Mensaje legible (sin datos personales)."""


# --------- cifrado por cuenta ---------


def _fernet(account_id: int) -> Fernet:
    raw = f"{settings.secret_key}|guest-registration|{account_id}".encode()
    return Fernet(urlsafe_b64encode(hashlib.sha256(raw).digest()))


def encrypt(account_id: int, data: dict) -> str:
    return _fernet(account_id).encrypt(json.dumps(data, ensure_ascii=False).encode()).decode()


def decrypt(account_id: int, blob: str | None) -> dict | None:
    if not blob:
        return None
    try:
        return json.loads(_fernet(account_id).decrypt(blob.encode()))
    except (InvalidToken, ValueError):
        return None


# --------- validación ---------

_NAME = re.compile(r"^[^\d<>{}\[\]@#$%^*=_|\\/~`]{1,60}$")
_DIGITS = re.compile(r"^\d{3,15}$")
_ALNUM = re.compile(r"^[A-Za-z0-9]{3,20}$")
_COUNTRY = re.compile(r"^[A-Z]{2}$")


def _clean(v, n: int = 80) -> str:
    return " ".join(str(v or "").split())[:n]


def _person(raw: dict, *, main: bool, today: date) -> tuple[dict, list[str]]:
    errs: list[str] = []
    doc_type = _clean(raw.get("doc_type"), 4).upper()
    allowed = MAIN_DOC_TYPES if main else set(DOC_TYPES)
    if doc_type not in allowed:
        errs.append("doc_type")
    number = re.sub(r"[\s.\-]", "", str(raw.get("doc_number") or "")).upper()
    pattern = _ALNUM if doc_type in ("PA", "CE") else _DIGITS
    if not pattern.match(number):
        errs.append("doc_number")
    first, last = _clean(raw.get("first_names"), 60), _clean(raw.get("last_names"), 60)
    if not first or not _NAME.match(first):
        errs.append("first_names")
    if not last or not _NAME.match(last):
        errs.append("last_names")
    nationality = _clean(raw.get("nationality"), 2).upper()
    if not _COUNTRY.match(nationality):
        errs.append("nationality")
    birth = _clean(raw.get("birth_date"), 10) or None
    if birth:
        try:
            b = date.fromisoformat(birth)
            if not (today - timedelta(days=365 * 120) < b <= today):
                errs.append("birth_date")
        except ValueError:
            errs.append("birth_date")
    elif nationality and nationality != "CO":
        errs.append("birth_date")  # SIRE la exige para extranjeros
    return {
        "doc_type": doc_type, "doc_number": number, "first_names": first, "last_names": last,
        "nationality": nationality, "birth_date": birth,
    }, errs


@dataclass
class Validated:
    data: dict
    errors: dict[str, list[str]]


def validate(raw: dict, today: date) -> Validated:
    """Normaliza y valida el formulario. `errors` por persona: {"main": [...], "c0": [...], "trip": [...]}."""
    errors: dict[str, list[str]] = {}
    main, e = _person(raw.get("main") or {}, main=True, today=today)
    if e:
        errors["main"] = e
    comps_raw = raw.get("companions") or []
    if not isinstance(comps_raw, list) or len(comps_raw) > MAX_COMPANIONS:
        errors["trip"] = ["companions"]
        comps_raw = []
    companions = []
    for i, c in enumerate(comps_raw):
        p, e = _person(c or {}, main=False, today=today)
        companions.append(p)
        if e:
            errors[f"c{i}"] = e
    trip = []
    motive = _clean(raw.get("motive"), 20)
    if motive not in MOTIVES:
        trip.append("motive")
    residence, origin = _clean(raw.get("residence_city")), _clean(raw.get("origin_city"))
    if not residence:
        trip.append("residence_city")
    if not origin:
        trip.append("origin_city")
    foreign = any(p["nationality"] and p["nationality"] != "CO" for p in [main, *companions])
    destination = _clean(raw.get("destination_city")) or None
    if foreign and not destination:
        trip.append("destination_city")
    if trip:
        errors.setdefault("trip", []).extend(trip)
    data = {"main": main, "companions": companions, "motive": motive, "residence_city": residence,
            "origin_city": origin, "destination_city": destination, "foreign": foreign}
    return Validated(data, errors)


# --------- registro por reserva ---------


async def get_settings(session: AsyncSession) -> RegistrationSettings:
    row = (await session.execute(select(RegistrationSettings))).scalar_one_or_none()
    if row is None:
        row = RegistrationSettings(accommodation={})
        session.add(row)
        await session.flush()
    return row


async def for_booking(session: AsyncSession, booking_id: int) -> GuestRegistration | None:
    return (await session.execute(
        select(GuestRegistration).where(GuestRegistration.booking_id == booking_id)
    )).scalar_one_or_none()


async def _booking(session: AsyncSession, booking_id: int) -> Booking:
    b = await session.get(Booking, booking_id)
    if b is None:
        raise LookupError("No existe esa reserva en tu cuenta")
    return b


async def ensure(session: AsyncSession, booking_id: int) -> GuestRegistration:
    """Crea (si falta) el registro con su enlace público."""
    b = await _booking(session, booking_id)
    reg = await for_booking(session, b.id)
    if reg is None:
        reg = GuestRegistration(booking_id=b.id, token=secrets.token_urlsafe(32), status=PENDING)
        session.add(reg)
        await session.flush()
    return reg


def link_open(b: Booking, reg: GuestRegistration, today: date) -> bool:
    """El enlace vale hasta el día de salida, si la reserva sigue en pie y la TRA no se envió."""
    return (b.status == BookingStatus.confirmed and b.check_out >= today and reg.tra_code is None
            and not reg.purged)


async def save(session: AsyncSession, reg: GuestRegistration, raw: dict, *, by: str, today: date) -> Validated:
    if reg.tra_code is not None:
        raise RegistrationError("La TRA ya se envió: las correcciones se hacen en la web del MinCIT.")
    v = validate(raw, today)
    if v.errors:
        return v
    reg.data_encrypted = encrypt(reg.account_id or current_account_id(session), v.data)
    reg.filled_by = by
    reg.submitted_at = _now()
    if by == "guest":
        reg.consent_at = _now()
    if reg.status in (PENDING, TRA_ERROR):
        reg.status = SUBMITTED
    await session.flush()
    return v


def data_of(reg: GuestRegistration) -> dict | None:
    return decrypt(reg.account_id, reg.data_encrypted)


# --------- costo ---------


async def proposed_cost(session: AsyncSession, b: Booking) -> Decimal | None:
    """Total de la reserva en COP (042). None si el canal no lo informa."""
    if b.amount is None:
        return None
    cur = (b.currency or "COP").upper()
    if cur == "COP":
        return Decimal(b.amount).quantize(Decimal("1"), ROUND_HALF_UP)
    from app.services import fx_service

    rate = await fx_service.rate_for(session, cur, b.check_in) or await fx_service.latest(session, cur)
    if rate is None:
        return None
    return (Decimal(b.amount) * rate).quantize(Decimal("1"), ROUND_HALF_UP)


# --------- TRA ---------


def missing_setup(s: RegistrationSettings, has_token: bool) -> list[str]:
    out = []
    if not (s.rnt or "").strip():
        out.append("rnt")
    if not (s.establishment_name or "").strip():
        out.append("establishment_name")
    if not has_token:
        out.append("token")
    if s.authorized_at is None:
        out.append("authorization")
    return out


def main_payload(d: dict, b: Booking, s: RegistrationSettings, accommodation: str, cost: Decimal) -> dict:
    m = d["main"]
    return {
        "tipo_identificacion": DOC_TYPES[m["doc_type"]],
        "numero_identificacion": m["doc_number"],
        "nombres": m["first_names"],
        "apellidos": m["last_names"],
        "cuidad_residencia": d["residence_city"],  # así, con la errata del MinCIT
        "cuidad_procedencia": d["origin_city"],
        "numero_habitacion": "1",  # vivienda completa
        "motivo": MOTIVES[d["motive"]],
        "numero_acompanantes": str(len(d["companions"])),
        "check_in": b.check_in.isoformat(),
        "check_out": b.check_out.isoformat(),
        "tipo_acomodacion": accommodation,
        "costo": str(int(cost)),
        "nombre_establecimiento": s.establishment_name.strip(),
        "rnt_establecimiento": re.sub(r"\D", "", s.rnt or ""),
    }


def companion_payload(c: dict, d: dict, b: Booking, parent: int) -> dict:
    return {
        "tipo_identificacion": DOC_TYPES[c["doc_type"]],
        "numero_identificacion": c["doc_number"],
        "nombres": c["first_names"],
        "apellidos": c["last_names"],
        "cuidad_residencia": d["residence_city"],
        "cuidad_procedencia": d["origin_city"],
        "numero_habitacion": "1",
        "check_in": b.check_in.isoformat(),
        "check_out": b.check_out.isoformat(),
        "padre": parent,
    }


def tra_client(token: str):
    """Cliente real con el token de la cuenta; en el ambiente de pruebas, el simulado."""
    from app.registration.tra import SimulatedTraClient, TraClient

    return SimulatedTraClient() if settings.sandbox else TraClient(token)


async def send_tra(session: AsyncSession, booking_id: int, client) -> GuestRegistration:
    """Envía al MinCIT lo que falte: el principal (si no tiene código) y cada acompañante
    pendiente. Reintentar no duplica al principal."""
    b = await _booking(session, booking_id)
    reg = await for_booking(session, b.id)
    if reg is None or reg.data_encrypted is None:
        raise RegistrationError("Aún no hay datos de los huéspedes para esta reserva.")
    d = data_of(reg)
    if d is None:
        raise RegistrationError("No se pudieron leer los datos guardados. Vuelve a llenarlos.")
    s = await get_settings(session)
    acc = (s.accommodation or {}).get(str(b.unit_type_id)) or "Apartamento"
    cost = Decimal(reg.cost_cop) if reg.cost_cop is not None else await proposed_cost(session, b)
    if cost is None:
        raise RegistrationError("Falta el costo total de la estadía (COP): escríbelo antes de enviar.")
    try:
        if reg.tra_code is None:
            reg.tra_code = await client.send_main(main_payload(d, b, s, acc, cost))
            reg.cost_cop = cost
        results = {r["i"]: r for r in (reg.tra_companions or []) if "code" in r}
        for i, c in enumerate(d["companions"]):
            if i in results:
                continue
            try:
                results[i] = {"i": i, "code": await client.send_companion(companion_payload(c, d, b, reg.tra_code))}
            except TraError as exc:
                results[i] = {"i": i, "error": str(exc)[:200]}
        reg.tra_companions = [results[i] for i in sorted(results)]
        failed = [r for r in reg.tra_companions if "error" in r]
        reg.status = TRA_PARTIAL if failed else TRA_SENT
        reg.tra_error = failed[0]["error"] if failed else None
        reg.tra_sent_at = _now()
        reg.tra_sent_by = current_user_id(session)
    except TraError as exc:
        reg.status = TRA_ERROR if reg.tra_code is None else TRA_PARTIAL
        reg.tra_error = str(exc)[:300]
    await session.flush()
    return reg


# --------- panel ---------


async def overview(session: AsyncSession, today: date) -> list[dict]:
    rows = (await session.execute(
        select(Booking).where(
            Booking.status == BookingStatus.confirmed,
            Booking.check_in <= today + timedelta(days=WINDOW_FUTURE),
            Booking.check_out >= today - timedelta(days=WINDOW_PAST),
        ).order_by(Booking.check_in, Booking.id)
    )).scalars().all()
    regs = {r.booking_id: r for r in (await session.execute(select(GuestRegistration))).scalars()}
    units = {u.id: u.name for u in (await session.execute(select(UnitType))).scalars()}
    out = []
    for b in rows:
        reg = regs.get(b.id)
        d = data_of(reg) if reg else None
        out.append({
            "booking_id": b.id, "ref": b.external_ref, "unit": units.get(b.unit_type_id),
            "channel": b.channel_kind.value, "check_in": b.check_in.isoformat(),
            "check_out": b.check_out.isoformat(), "guest_name": b.guest_name,
            "status": reg.status if reg else None,
            "token": reg.token if reg and link_open(b, reg, today) else None,
            "filled_by": reg.filled_by if reg else None,
            "guests": (1 + len(d["companions"])) if d else None,
            "foreign": bool(d and d.get("foreign")),
            "tra_sent_at": reg.tra_sent_at.isoformat() if reg and reg.tra_sent_at else None,
            "tra_error": reg.tra_error if reg else None,
        })
    return out


async def detail(session: AsyncSession, booking_id: int, today: date) -> dict:
    b = await _booking(session, booking_id)
    reg = await for_booking(session, b.id)
    s = await get_settings(session)
    proposal = await proposed_cost(session, b)
    return {
        "booking_id": b.id, "ref": b.external_ref, "channel": b.channel_kind.value,
        "check_in": b.check_in.isoformat(), "check_out": b.check_out.isoformat(),
        "guest_name": b.guest_name,
        "unit": (await session.get(UnitType, b.unit_type_id)).name if b.unit_type_id else None,
        "accommodation": (s.accommodation or {}).get(str(b.unit_type_id)) or "Apartamento",
        "status": reg.status if reg else None,
        "token": reg.token if reg and link_open(b, reg, today) else None,
        "data": data_of(reg) if reg else None,
        "filled_by": reg.filled_by if reg else None,
        "cost_cop": str(reg.cost_cop) if reg and reg.cost_cop is not None else None,
        "cost_proposed": str(proposal) if proposal is not None else None,
        "tra_code": reg.tra_code if reg else None,
        "tra_companions": reg.tra_companions if reg else None,
        "tra_error": reg.tra_error if reg else None,
        "tra_sent_at": reg.tra_sent_at.isoformat() if reg and reg.tra_sent_at else None,
        "editable": reg is None or reg.tra_code is None,
    }


# --------- aviso al anfitrión ---------

_PUSH = {
    "es": ("Datos de huéspedes recibidos", "{dates}. Revísalos y envía la TRA en StayLever."),
    "en": ("Guest details received", "{dates}. Review them and send the TRA in StayLever."),
    "pt": ("Dados dos hóspedes recebidos", "{dates}. Revise e envie a TRA no StayLever."),
}


async def notify_submitted(session: AsyncSession, reg: GuestRegistration, b: Booking) -> None:
    """Aviso al celular cuando el huésped envía sus datos (sin nombres). Nunca lanza."""
    from app.services import push_service

    try:
        lang = await push_service._lang(session)
        title, body = _PUSH.get(lang, _PUSH["es"])
        await push_service.notify(
            session, kind="guest-reg", ref=str(b.id), fingerprint=reg.submitted_at.isoformat(),
            title=title, body=body.format(dates=push_service._range(b.check_in, b.check_out, lang)),
            url=f"/registration?booking={b.id}", pref=push_service.PREF_BOOKINGS,
        )
    except Exception:  # noqa: BLE001 — el aviso nunca rompe el registro
        pass


# --------- retención (028) ---------


async def purge(session: AsyncSession, account_id: int, cutoff: date) -> int:
    """Borra los datos cifrados de registros con salida anterior a `cutoff` (1 año, 028)."""
    rows = (await session.execute(
        select(GuestRegistration).join(Booking, Booking.id == GuestRegistration.booking_id).where(
            GuestRegistration.account_id == account_id,
            GuestRegistration.purged.is_(False),
            Booking.check_out < cutoff,
        )
    )).scalars().all()
    for r in rows:
        r.data_encrypted = None
        r.purged = True
    await session.flush()
    return len(rows)
