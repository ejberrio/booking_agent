"""Modo sin conexión (feature 029): el anfitrión crea su apartamento a mano.

StayLever se vuelve la "verdad" de precios y ocupación de la cuenta: el calendario se siembra
con el precio entre semana y el de fin de semana (noches de viernes y sábado), la ocupación
llega de los calendarios iCal de Airbnb/Booking (`ical_service`) o se marca a mano, y las
sugerencias y el asistente funcionan igual, sin publicar nada: el anfitrión aplica los precios
en cada plataforma con los enlaces que la app le muestra.
"""

from __future__ import annotations

import re
import uuid
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.factory import MANUAL, set_channel_mode
from app.models.account import Account
from app.models.calendar import CalendarDay, Rate
from app.models.enums import ChannelKind
from app.models.property import Channel, Property, UnitType

PROVIDER = "manual"
SEED_DAYS = 365
WEEKEND = (4, 5)  # noches de viernes y sábado (mismo criterio que price_extension)
MAX_MANUAL_UNITS = 5
_AIRBNB_ROOM = re.compile(r"airbnb\.[a-z.]+/(?:rooms|h)/(\d+)")


class ManualError(ValueError):
    """Datos inválidos del apartamento manual."""


@dataclass
class ManualListing:
    kind: ChannelKind
    listing_url: str | None = None
    ical_url: str | None = None


def _url(value: str | None, limit: int) -> str | None:
    """Normaliza a https: acepta 'www.booking.com/…', 'http://…' y 'webcal://…' (iCal)."""
    value = (value or "").strip()
    if not value:
        return None
    scheme, sep, rest = value.partition("://")
    if not sep:
        rest = value
    elif scheme.lower() not in ("http", "https", "webcal"):
        raise ManualError("ese enlace no es válido (cópialo desde la plataforma).")
    value = "https://" + rest
    host = (urlparse(value).hostname or "")
    if "." not in host or len(value) > limit:
        raise ManualError("ese enlace no es válido (cópialo desde la plataforma).")
    return value


def calendar_links(channel: Channel) -> dict:
    """Enlaces para aplicar un precio a mano en cada plataforma."""
    if channel.kind == ChannelKind.airbnb:
        m = _AIRBNB_ROOM.search(channel.listing_url or "")
        url = (
            f"https://www.airbnb.com/multicalendar/{m.group(1)}" if m
            else "https://www.airbnb.com/multicalendar"
        )
        return {"channel": "airbnb", "calendar_url": url, "listing_url": channel.listing_url}
    if channel.kind == ChannelKind.booking:
        return {"channel": "booking", "calendar_url": "https://admin.booking.com/",
                "listing_url": channel.listing_url}
    return {"channel": channel.kind.value, "calendar_url": None, "listing_url": channel.listing_url}


async def create_apartment(
    session: AsyncSession,
    account_id: int,
    *,
    name: str,
    city: str,
    currency: str = "COP",
    weekday_price: Decimal,
    weekend_price: Decimal | None = None,
    listings: list[ManualListing] | None = None,
    today: date | None = None,
) -> UnitType:
    """Crea propiedad + unidad + canales y siembra 365 noches de precio y disponibilidad."""
    name, city = (name or "").strip(), (city or "").strip()
    if not name or not city:
        raise ManualError("indica el nombre del apartamento y la ciudad.")
    if weekday_price <= 0 or (weekend_price is not None and weekend_price <= 0):
        raise ManualError("los precios deben ser mayores que 0.")
    count = len(
        (await session.execute(select(Property.id).where(Property.provider == PROVIDER))).all()
    )
    if count >= MAX_MANUAL_UNITS:
        raise ManualError(f"máximo {MAX_MANUAL_UNITS} apartamentos sin conexión por cuenta.")
    acc = await session.get(Account, account_id)
    has_connected = (
        await session.execute(select(Property.id).where(Property.provider != PROVIDER))
    ).first() is not None
    if acc.channel_mode != MANUAL and has_connected:
        raise ManualError("esta cuenta ya está conectada a un Channel Manager.")

    ref = f"manual-{uuid.uuid4().hex[:12]}"
    prop = Property(name=name[:200], city=city[:120], currency=(currency or "COP")[:3].upper(),
                    provider=PROVIDER, external_ref=ref)
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name=name[:200], units_count=1, external_ref=ref)
    session.add(unit)
    await session.flush()
    for listing in listings or []:
        session.add(
            Channel(
                property_id=prop.id,
                kind=listing.kind,
                is_active=True,
                listing_url=_url(listing.listing_url, 500),
                ical_url=_url(listing.ical_url, 1000),
            )
        )
    today = today or date.today()
    weekend_price = weekend_price or weekday_price
    for i in range(SEED_DAYS):
        d = today + timedelta(days=i)
        price = weekend_price if d.weekday() in WEEKEND else weekday_price
        # Siembra inicial: precio de partida del anfitrión, sin entradas de auditoría.
        session.add(Rate(unit_type_id=unit.id, date=d, base_price=price))
        session.add(CalendarDay(unit_type_id=unit.id, date=d, units_available=1, is_blocked=False))
    acc.channel_mode = MANUAL
    set_channel_mode(session, MANUAL)
    await session.flush()
    return unit


async def update_listings(
    session: AsyncSession, property_id: int, listings: list[ManualListing]
) -> list[Channel]:
    prop = await session.get(Property, property_id)
    if prop is None or prop.provider != PROVIDER:
        raise ManualError("ese apartamento no existe o no es sin conexión.")
    current = {
        c.kind: c
        for c in (
            await session.execute(select(Channel).where(Channel.property_id == property_id))
        ).scalars()
    }
    for listing in listings:
        ch = current.get(listing.kind)
        if ch is None:
            ch = Channel(property_id=property_id, kind=listing.kind, is_active=True)
            session.add(ch)
            current[listing.kind] = ch
        ch.listing_url = _url(listing.listing_url, 500)
        ch.ical_url = _url(listing.ical_url, 1000)
        ch.is_active = True
    await session.flush()
    return list(current.values())


async def overview(session: AsyncSession) -> list[dict]:
    """Apartamentos sin conexión de la cuenta con sus canales y enlaces."""
    props = (
        await session.execute(
            select(Property).where(Property.provider == PROVIDER).order_by(Property.id)
        )
    ).scalars().all()
    out = []
    for p in props:
        unit = (
            await session.execute(select(UnitType).where(UnitType.property_id == p.id))
        ).scalars().first()
        channels = (
            await session.execute(
                select(Channel).where(Channel.property_id == p.id).order_by(Channel.kind)
            )
        ).scalars().all()
        out.append({
            "property_id": p.id,
            "unit_type_id": unit.id if unit else None,
            "name": p.name,
            "city": p.city,
            "currency": p.currency,
            "channels": [
                # El enlace iCal da acceso al calendario: solo se muestra el inicio.
                {**calendar_links(c), "has_ical": bool(c.ical_url),
                 "ical_hint": (c.ical_url[:32] + "…") if c.ical_url else None}
                for c in channels
            ],
        })
    return out
