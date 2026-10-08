"""Registro informativo de deals nativos (feature 015).

Los deals nativos (badge de Booking, semanal/mensual de Airbnb) no tienen API:
el host los ANOTA aquí. Este servicio nunca llama al Channel Manager — es un
registro local para el calendario y la advertencia real de doble descuento.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ChannelKind
from app.models.pricing import NativeDeal

_MANAGED = {ChannelKind.booking, ChannelKind.airbnb}
_UNSET = object()


class NativeDealError(ValueError):
    """Datos inválidos para el registro de deals."""


def _validate(channel: ChannelKind, name: str, pct: Decimal, date_from, date_to) -> None:
    if channel not in _MANAGED:
        raise NativeDealError("El canal debe ser booking o airbnb")
    if not name or not name.strip():
        raise NativeDealError("El nombre del deal es obligatorio")
    if not (Decimal(0) <= pct <= Decimal(100)):
        raise NativeDealError("El descuento debe estar entre 0 y 100%")
    if date_from is not None and date_to is not None and date_from > date_to:
        raise NativeDealError("La fecha de fin no puede ser anterior a la de inicio")


STACKING = ("always", "conditional")


def _stacking(value, name: str) -> str:
    """Valor explícito validado; sin valor, por nombre: móvil → always (feature 022)."""
    if value is None:
        low = (name or "").lower()
        return "always" if any(k in low for k in ("mobile", "móvil", "movil")) else "conditional"
    if value not in STACKING:
        raise NativeDealError("La acumulación debe ser always o conditional")
    return value


def _covers(deal: NativeDeal, day: date) -> bool:
    return (deal.date_from is None or deal.date_from <= day) and (
        deal.date_to is None or deal.date_to >= day
    )


async def always_pct_for(session: AsyncSession, day: date) -> dict[str, Decimal]:
    """% acumulado de deals ACTIVOS 'always' que cubren la noche, por canal (feature 022)."""
    out: dict[str, Decimal] = {"booking": Decimal(0), "airbnb": Decimal(0)}
    deals = (
        await session.execute(
            select(NativeDeal).where(NativeDeal.is_active.is_(True), NativeDeal.stacking == "always")
        )
    ).scalars()
    for d in deals:
        if _covers(d, day):
            out[d.channel.value] = out.get(d.channel.value, Decimal(0)) + d.discount_pct
    return out


async def conditional_deals_for(session: AsyncSession, first: date, last: date) -> list[NativeDeal]:
    """Deals ACTIVOS 'conditional' que solapan el rango (aviso informativo)."""
    return [d for d in await find_overlapping(session, first, last) if d.stacking != "always"]


async def list_deals(session: AsyncSession) -> list[NativeDeal]:
    stmt = select(NativeDeal).order_by(
        NativeDeal.channel, NativeDeal.date_from.asc().nulls_first(), NativeDeal.id
    )
    return list((await session.execute(stmt)).scalars())


async def create(
    session: AsyncSession,
    *,
    channel: ChannelKind,
    name: str,
    discount_pct: Decimal,
    date_from: date | None = None,
    date_to: date | None = None,
    is_active: bool = True,
    stacking: str | None = None,
) -> NativeDeal:
    _validate(channel, name, discount_pct, date_from, date_to)
    deal = NativeDeal(
        channel=channel,
        name=name.strip(),
        discount_pct=discount_pct,
        date_from=date_from,
        date_to=date_to,
        is_active=is_active,
        stacking=_stacking(stacking, name),
    )
    session.add(deal)
    await session.flush()
    return deal


async def update(
    session: AsyncSession,
    deal_id: int,
    *,
    channel: ChannelKind | object = _UNSET,
    name: str | object = _UNSET,
    discount_pct: Decimal | object = _UNSET,
    date_from: date | None | object = _UNSET,
    date_to: date | None | object = _UNSET,
    is_active: bool | object = _UNSET,
    stacking: str | object = _UNSET,
) -> NativeDeal:
    """Actualización parcial; date_from/date_to aceptan None explícito para abrir el extremo."""
    deal = await session.get(NativeDeal, deal_id)
    if deal is None:
        raise LookupError(f"No existe el deal {deal_id}")
    new_channel = deal.channel if channel is _UNSET else channel
    new_name = deal.name if name is _UNSET else name
    new_pct = deal.discount_pct if discount_pct is _UNSET else discount_pct
    new_from = deal.date_from if date_from is _UNSET else date_from
    new_to = deal.date_to if date_to is _UNSET else date_to
    _validate(new_channel, new_name, new_pct, new_from, new_to)
    deal.channel = new_channel
    deal.name = new_name.strip()
    deal.discount_pct = new_pct
    deal.date_from = new_from
    deal.date_to = new_to
    if is_active is not _UNSET:
        deal.is_active = is_active
    if stacking is not _UNSET:
        deal.stacking = _stacking(stacking, deal.name)
    await session.flush()
    return deal


async def delete(session: AsyncSession, deal_id: int) -> None:
    deal = await session.get(NativeDeal, deal_id)
    if deal is None:
        raise LookupError(f"No existe el deal {deal_id}")
    await session.delete(deal)
    await session.flush()


async def find_overlapping(
    session: AsyncSession,
    first_night: date,
    last_night: date,
    channels_scope: list[str] | None = None,
) -> list[NativeDeal]:
    """Deals ACTIVOS que solapan el rango y el alcance de canales (None = todos).

    Extremos abiertos: date_from/date_to en NULL solapan siempre por ese lado.
    """
    stmt = (
        select(NativeDeal)
        .where(
            NativeDeal.is_active.is_(True),
            (NativeDeal.date_from.is_(None)) | (NativeDeal.date_from <= last_night),
            (NativeDeal.date_to.is_(None)) | (NativeDeal.date_to >= first_night),
        )
        .order_by(NativeDeal.channel, NativeDeal.id)
    )
    deals = list((await session.execute(stmt)).scalars())
    if channels_scope is None:
        return deals
    return [d for d in deals if d.channel.value in channels_scope]
