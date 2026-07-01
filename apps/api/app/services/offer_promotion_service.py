"""Promociones publicadas como 'fixed price' sobre una oferta designada (feature 011).

A diferencia del `promotion_service` clásico (que recorta el precio BASE del
calendario), aquí la promoción se publica al Channel Manager como una oferta con
nombre (fixed price) sobre la oferta designada por config `beds24_promo_offer_id`.

Patrón humano-en-el-bucle: preview → apply(confirm) → publish → auditar. La
retirada neutraliza (roomPriceEnable=false) y oculta. Se apoya en el modelo
`Promotion` existente (columnas offer_id/external_id/unit_type_id + conditions).
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelManager, RemoteFixedPrice
from app.core.config import settings
from app.models.audit import PromotionChangeLog
from app.models.booking import Booking
from app.models.enums import (
    BookingStatus,
    ChangeOrigin,
    PromotionAction,
    PromotionStatus,
    PromotionType,
)
from app.models.pricing import Promotion
from app.models.property import UnitType
from app.schemas.promotion import (
    PromotionApplyResult,
    PromotionPreview,
    PromotionView,
    promotion_fingerprint,
)


class PromotionError(ValueError):
    """Error de dominio de promociones (mensaje apto para el host / loop del agente)."""


def _designated_offer_id() -> int:
    """Oferta destino de las promociones.

    Verificado en vivo (2026-07-01): Beds24 asigna los fixed prices a la oferta
    pública principal (offerId=1) sin importar el valor enviado; el "slot" no es
    seleccionable por API. Por eso el destino es 1 por defecto; BEDS24_PROMO_OFFER_ID
    queda como override opcional por si el canal empezara a respetarlo.
    """
    return int(settings.beds24_promo_offer_id or 1)


def _round_cop(value: Decimal) -> Decimal:
    """Redondea a entero (COP no usa decimales)."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


async def _base_price(
    session: AsyncSession, adapter: ChannelManager, unit: UnitType, day: date
) -> Decimal | None:
    if not unit.external_ref:
        return None
    rates = await adapter.get_rates(unit.external_ref, day, day)
    for r in rates:
        if r.date == day and r.price > 0:
            return r.price
    return rates[0].price if rates else None


async def _booked_nights(session: AsyncSession, unit_id: int, start: date, end: date) -> int:
    res = await session.execute(
        select(Booking).where(
            Booking.unit_type_id == unit_id,
            Booking.status == BookingStatus.confirmed,
            Booking.check_in <= end,
            Booking.check_out > start,
        )
    )
    return len(list(res.scalars()))


async def _overlaps(
    session: AsyncSession, unit_id: int, start: date, end: date, exclude_id: int | None
) -> list[Promotion]:
    res = await session.execute(
        select(Promotion).where(
            Promotion.unit_type_id == unit_id,
            Promotion.offer_id.is_not(None),
            Promotion.status == PromotionStatus.active,
            Promotion.start_date <= end,
            Promotion.end_date >= start,
        )
    )
    return [p for p in res.scalars() if exclude_id is None or p.id != exclude_id]


def _conditions(base: Decimal | None, price: Decimal, min_nights: int | None, published: bool) -> dict:
    return {
        "offer": True,
        "base_price": str(base) if base is not None else None,
        "price": str(price),
        "min_nights": min_nights,
        "published": published,
    }


def _price_of(p: Promotion) -> Decimal:
    c = p.conditions or {}
    return Decimal(str(c.get("price", p.discount_value)))


def _base_of(p: Promotion) -> Decimal | None:
    c = p.conditions or {}
    return Decimal(str(c["base_price"])) if c.get("base_price") is not None else None


def _view(p: Promotion) -> PromotionView:
    c = p.conditions or {}
    price = _price_of(p)
    base = _base_of(p)
    published = bool(c.get("published"))
    if p.status == PromotionStatus.inactive:
        status = "retired"
    elif published:
        status = "published"
    else:
        status = "sync_error"
    return PromotionView(
        id=p.id,
        name=p.name,
        offer_id=p.offer_id,
        first_night=p.start_date,
        last_night=p.end_date,
        base_price=base,
        price=price,
        discount_pct=p.discount_value if p.discount_type == PromotionType.percent else None,
        saving=(base - price) if base is not None else None,
        min_nights=c.get("min_nights"),
        status=status,
        published=published,
    )


def _snapshot(p: Promotion) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "offer_id": p.offer_id,
        "first_night": p.start_date.isoformat(),
        "last_night": p.end_date.isoformat(),
        "price": str(_price_of(p)),
        "status": p.status.value,
    }


async def preview(
    session: AsyncSession,
    adapter: ChannelManager,
    *,
    unit_type_id: int,
    first_night: date,
    last_night: date,
    name: str,
    discount_pct: Decimal | None = None,
    price: Decimal | None = None,
    min_nights: int | None = None,
    exclude_id: int | None = None,
) -> PromotionPreview:
    offer_id = _designated_offer_id()
    unit = await session.get(UnitType, unit_type_id)
    if unit is None:
        raise PromotionError(f"No existe la unidad {unit_type_id}")

    # Fechas
    if last_night < first_night:
        raise PromotionError("La última noche no puede ser anterior a la primera.")
    if last_night < date.today():
        raise PromotionError("El rango de la promoción está en el pasado.")
    if min_nights is not None and min_nights < 1:
        raise PromotionError("La estancia mínima debe ser al menos 1 noche.")

    base = await _base_price(session, adapter, unit, first_night)

    # Precio con descuento
    if discount_pct is not None:
        if not (Decimal(0) < discount_pct < Decimal(100)):
            raise PromotionError("El descuento debe estar entre 0% y 100%.")
        if base is None:
            raise PromotionError(
                "No hay precio base para esas fechas; indica un precio con descuento absoluto."
            )
        final_price = _round_cop(base * (Decimal(1) - discount_pct / Decimal(100)))
    elif price is not None:
        final_price = _round_cop(Decimal(price))
    else:
        raise PromotionError("Indica un descuento en porcentaje o un precio con descuento.")

    if final_price <= 0:
        raise PromotionError("El precio con descuento debe ser mayor que 0.")
    if base is not None and final_price >= base:
        raise PromotionError(
            f"El precio con descuento ({final_price}) no es menor que el precio base ({base})."
        )

    pct = discount_pct
    if pct is None and base is not None and base > 0:
        pct = _round_cop((Decimal(1) - final_price / base) * Decimal(100))
    saving = (base - final_price) if base is not None else None

    warnings: list[str] = []
    overlaps = await _overlaps(session, unit_type_id, first_night, last_night, exclude_id)
    if overlaps:
        names = ", ".join(f"'{o.name}'" for o in overlaps)
        warnings.append(f"Se solapa con otra promoción activa: {names}. Confirma para continuar.")
    booked = await _booked_nights(session, unit_type_id, first_night, last_night)
    if booked:
        warnings.append(
            f"Hay {booked} reserva(s) confirmada(s) en el rango; sus precios no cambian "
            "(la promoción afecta solo a nuevas reservas)."
        )

    return PromotionPreview(
        offer_id=offer_id,
        first_night=first_night,
        last_night=last_night,
        name=name,
        base_price=base,
        price=final_price,
        discount_pct=pct,
        saving=saving,
        min_nights=min_nights,
        warnings=warnings,
        valid=True,
        fingerprint=promotion_fingerprint(offer_id, first_night, last_night, final_price, base),
    )


async def apply(
    session: AsyncSession,
    adapter: ChannelManager,
    *,
    unit_type_id: int,
    first_night: date,
    last_night: date,
    name: str,
    fingerprint: str | None = None,
    discount_pct: Decimal | None = None,
    price: Decimal | None = None,
    min_nights: int | None = None,
    promotion_id: int | None = None,
    confirm_overlap: bool = False,
    origin: ChangeOrigin = ChangeOrigin.manual,
) -> PromotionApplyResult:
    prev = await preview(
        session,
        adapter,
        unit_type_id=unit_type_id,
        first_night=first_night,
        last_night=last_night,
        name=name,
        discount_pct=discount_pct,
        price=price,
        min_nights=min_nights,
        exclude_id=promotion_id,
    )
    if fingerprint is not None and prev.fingerprint != fingerprint:
        raise PromotionError("La propuesta quedó obsoleta (cambió el precio base o el estado). Revísala de nuevo.")
    has_overlap = any("solapa" in w for w in prev.warnings)
    if has_overlap and not confirm_overlap:
        raise PromotionError(prev.warnings[0])

    unit = await session.get(UnitType, unit_type_id)
    existing = await session.get(Promotion, promotion_id) if promotion_id else None
    before = _snapshot(existing) if existing else None

    if existing is None:
        promo = Promotion(
            property_id=unit.property_id,
            unit_type_id=unit_type_id,
            offer_id=prev.offer_id,
            name=name,
            discount_type=PromotionType.percent,
            discount_value=prev.discount_pct or Decimal(0),
            start_date=first_night,
            end_date=last_night,
            status=PromotionStatus.active,
            conditions=_conditions(prev.base_price, prev.price, min_nights, published=False),
        )
        session.add(promo)
        await session.flush()
    else:
        promo = existing
        promo.name = name
        promo.discount_value = prev.discount_pct or Decimal(0)
        promo.start_date = first_night
        promo.end_date = last_night
        promo.status = PromotionStatus.active
        promo.conditions = _conditions(prev.base_price, prev.price, min_nights, published=False)
        await session.flush()

    # Publicar como fixed price
    from app.services import sync_service

    fp = RemoteFixedPrice(
        offer_id=prev.offer_id,
        room_external_id=unit.external_ref or "",
        first_night=first_night,
        last_night=last_night,
        name=name,
        price=prev.price,
        external_id=promo.external_id,
        price_enabled=True,
        min_nights=min_nights,
    )
    external_id, issue = await sync_service.publish_promotion(session, adapter, fp)
    if external_id is not None:
        promo.external_id = external_id
    conditions = dict(promo.conditions or {})
    conditions["published"] = issue is None
    promo.conditions = conditions
    await session.flush()

    session.add(
        PromotionChangeLog(
            promotion_id=promo.id,
            action=PromotionAction.updated if existing else PromotionAction.created,
            before=before,
            after=_snapshot(promo),
            origin=origin,
        )
    )
    await session.flush()

    return PromotionApplyResult(
        id=promo.id,
        status="published" if issue is None else "sync_error",
        external_id=promo.external_id,
        published=issue is None,
        issue=issue,
    )


async def retire(
    session: AsyncSession,
    adapter: ChannelManager,
    promotion_id: int,
    *,
    confirm: bool = True,
    origin: ChangeOrigin = ChangeOrigin.manual,
) -> PromotionApplyResult:
    promo = await session.get(Promotion, promotion_id)
    if promo is None or promo.offer_id is None:
        raise PromotionError(f"No existe la promoción {promotion_id}.")
    if not confirm:
        raise PromotionError("La retirada requiere confirmación.")
    before = _snapshot(promo)
    unit = await session.get(UnitType, promo.unit_type_id) if promo.unit_type_id else None

    from app.services import sync_service

    issue = None
    if promo.external_id is not None and unit is not None and unit.external_ref:
        issue = await sync_service.retire_promotion(
            session,
            adapter,
            external_id=promo.external_id,
            room_external_id=unit.external_ref,
            offer_id=promo.offer_id,
        )

    promo.status = PromotionStatus.inactive
    conditions = dict(promo.conditions or {})
    conditions["published"] = False
    promo.conditions = conditions
    await session.flush()

    session.add(
        PromotionChangeLog(
            promotion_id=promo.id,
            action=PromotionAction.updated,
            before=before,
            after=_snapshot(promo),
            origin=origin,
        )
    )
    await session.flush()

    return PromotionApplyResult(
        id=promo.id,
        status="retired" if issue is None else "sync_error",
        external_id=promo.external_id,
        published=False,
        issue=issue,
    )


async def list_promotions(session: AsyncSession, unit_type_id: int) -> list[PromotionView]:
    res = await session.execute(
        select(Promotion)
        .where(Promotion.unit_type_id == unit_type_id, Promotion.offer_id.is_not(None))
        .order_by(Promotion.start_date)
    )
    return [_view(p) for p in res.scalars()]
