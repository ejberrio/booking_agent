from dataclasses import asdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.sync import get_adapter
from app.db.session import get_session
from app.channels.errors import ChannelError
from app.models.enums import ChangeOrigin, ChannelKind, PromotionType
from app.schemas.pricing import RangeSelection
from app.services import (
    availability_service,
    channel_pricing_service,
    native_deal_service,
    offer_promotion_service,
    price_extension_service,
    pricing_app_service,
    promotion_service,
)
from app.services.audit_service import RollbackConflict
from app.services.channel_pricing_service import ChannelOffsetError, FingerprintError
from app.services.native_deal_service import NativeDealError
from app.services.offer_promotion_service import PromotionError
from app.services.price_extension_service import ExtensionError, ExtensionParams, MonthInput

router = APIRouter()


class DayPriceRequest(BaseModel):
    unit_type_id: int
    day: date
    price: Decimal


class SelectionBody(BaseModel):
    date_from: date
    date_to: date
    weekdays: list[int] | None = None
    days: list[date] | None = None

    def to_selection(self) -> RangeSelection:
        return RangeSelection(self.date_from, self.date_to, self.weekdays, self.days)


class RangePreviewRequest(BaseModel):
    unit_type_id: int
    selection: SelectionBody
    price: Decimal


class RangeApplyRequest(RangePreviewRequest):
    fingerprint: str


class AvailabilityPreviewRequest(BaseModel):
    unit_type_id: int
    action: str  # "block" | "open"
    selection: SelectionBody


class AvailabilityApplyRequest(AvailabilityPreviewRequest):
    fingerprint: str


class RollbackRequest(BaseModel):
    change_id: int
    confirm: bool = False


class PromotionRequest(BaseModel):
    property_id: int
    name: str
    discount_type: PromotionType
    discount_value: Decimal
    start_date: date
    end_date: date
    conditions: dict | None = None


class OfferPromoPreviewRequest(BaseModel):
    unit_type_id: int
    first_night: date
    last_night: date
    name: str
    discount_pct: Decimal | None = None
    price: Decimal | None = None
    min_nights: int | None = None
    promotion_id: int | None = None  # presente = edición
    channels_scope: list[str] | None = None  # None = todos los canales


class OfferPromoApplyRequest(OfferPromoPreviewRequest):
    fingerprint: str
    confirm_overlap: bool = False


class OfferPromoRetireRequest(BaseModel):
    id: int
    confirm: bool = True


class ChannelOffsetPreviewRequest(BaseModel):
    channel: str
    offset_pct: Decimal


class ChannelOffsetApplyRequest(ChannelOffsetPreviewRequest):
    fingerprint: str


class NativeDealCreateRequest(BaseModel):
    channel: str
    name: str
    discount_pct: Decimal
    date_from: date | None = None
    date_to: date | None = None
    is_active: bool = True
    stacking: str | None = None  # feature 022: always | conditional (None = por nombre)


class NativeDealUpdateRequest(BaseModel):
    # Parcial: solo lo enviado se actualiza; date_from/date_to aceptan null explícito.
    channel: str | None = None
    name: str | None = None
    discount_pct: Decimal | None = None
    date_from: date | None = None
    date_to: date | None = None
    is_active: bool | None = None
    stacking: str | None = None


class MinPriceRequest(BaseModel):
    min_price: Decimal | None = None


@router.get("/calendar")
async def calendar(
    unit_type_id: int, date_from: date, date_to: date, session: AsyncSession = Depends(get_session)
):
    views = await pricing_app_service.get_calendar(session, unit_type_id, date_from, date_to)
    return [asdict(v) for v in views]


@router.get("/kpis")
async def kpis(
    unit_type_id: int, date_from: date, date_to: date, session: AsyncSession = Depends(get_session)
):
    return await pricing_app_service.get_kpis(session, unit_type_id, date_from, date_to)


# --------- deals nativos (feature 015: registro informativo local) ---------


def _deal_view(d) -> dict:
    return {
        "id": d.id,
        "channel": d.channel.value,
        "name": d.name,
        "discount_pct": str(d.discount_pct),
        "date_from": d.date_from.isoformat() if d.date_from else None,
        "date_to": d.date_to.isoformat() if d.date_to else None,
        "is_active": d.is_active,
        "stacking": d.stacking,
    }


def _deal_channel(value: str) -> ChannelKind:
    try:
        return ChannelKind(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="El canal debe ser booking o airbnb") from exc


@router.get("/native-deals")
async def list_native_deals(session: AsyncSession = Depends(get_session)):
    deals = await native_deal_service.list_deals(session)
    return {"deals": [_deal_view(d) for d in deals]}


@router.post("/native-deals")
async def create_native_deal(
    req: NativeDealCreateRequest, session: AsyncSession = Depends(get_session)
):
    try:
        deal = await native_deal_service.create(
            session,
            channel=_deal_channel(req.channel),
            name=req.name,
            discount_pct=req.discount_pct,
            date_from=req.date_from,
            date_to=req.date_to,
            is_active=req.is_active,
            stacking=req.stacking,
        )
        await session.commit()
        return _deal_view(deal)
    except NativeDealError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/native-deals/{deal_id}")
async def update_native_deal(
    deal_id: int, req: NativeDealUpdateRequest, session: AsyncSession = Depends(get_session)
):
    kwargs: dict = {}
    sent = req.model_fields_set
    if "channel" in sent and req.channel is not None:
        kwargs["channel"] = _deal_channel(req.channel)
    if "name" in sent and req.name is not None:
        kwargs["name"] = req.name
    if "discount_pct" in sent and req.discount_pct is not None:
        kwargs["discount_pct"] = req.discount_pct
    if "date_from" in sent:
        kwargs["date_from"] = req.date_from  # null explícito = abrir el extremo
    if "date_to" in sent:
        kwargs["date_to"] = req.date_to
    if "is_active" in sent and req.is_active is not None:
        kwargs["is_active"] = req.is_active
    if "stacking" in sent and req.stacking is not None:
        kwargs["stacking"] = req.stacking
    try:
        deal = await native_deal_service.update(session, deal_id, **kwargs)
        await session.commit()
        return _deal_view(deal)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NativeDealError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# --------- precio mínimo por noche (feature 022) ---------


async def _rule(session: AsyncSession, *, create: bool):
    from sqlalchemy import select

    from app.models.pricing import PricingRule
    from app.models.property import Property

    rule = (
        await session.execute(select(PricingRule).order_by(PricingRule.id))
    ).scalars().first()
    if rule is None and create:
        prop = (await session.execute(select(Property).order_by(Property.id))).scalars().first()
        if prop is None:
            raise HTTPException(status_code=409, detail="no hay propiedad sincronizada; importa desde el Channel Manager")
        rule = PricingRule(property_id=prop.id, is_active=True)
        session.add(rule)
        await session.flush()
    return rule


@router.get("/min-price")
async def get_min_price(session: AsyncSession = Depends(get_session)):
    rule = await _rule(session, create=False)
    value = rule.min_price if rule and rule.is_active else None
    return {"min_price": f"{value:.2f}" if value is not None else None}


@router.put("/min-price")
async def put_min_price(req: MinPriceRequest, session: AsyncSession = Depends(get_session)):
    if req.min_price is not None and req.min_price <= 0:
        raise HTTPException(status_code=422, detail="El precio mínimo debe ser mayor que 0")
    rule = await _rule(session, create=True)
    rule.min_price = req.min_price
    rule.is_active = True
    await session.commit()
    return {"min_price": f"{rule.min_price:.2f}" if rule.min_price is not None else None}


@router.delete("/native-deals/{deal_id}")
async def delete_native_deal(deal_id: int, session: AsyncSession = Depends(get_session)):
    try:
        await native_deal_service.delete(session, deal_id)
        await session.commit()
        return {"deleted": True}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/day")
async def set_day(req: DayPriceRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        result = await pricing_app_service.set_day_price(
            session, adapter, unit_type_id=req.unit_type_id, day=req.day, price=req.price
        )
        await session.commit()
        return asdict(result)
    finally:
        await adapter.aclose()


@router.post("/range/preview")
async def range_preview(req: RangePreviewRequest, session: AsyncSession = Depends(get_session)):
    preview = await pricing_app_service.preview_range(
        session, unit_type_id=req.unit_type_id, selection=req.selection.to_selection(), price=req.price
    )
    return asdict(preview)


@router.post("/range/apply")
async def range_apply(req: RangeApplyRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        result = await pricing_app_service.apply_range(
            session,
            adapter,
            unit_type_id=req.unit_type_id,
            selection=req.selection.to_selection(),
            price=req.price,
            fingerprint=req.fingerprint,
        )
        await session.commit()
        return asdict(result)
    finally:
        await adapter.aclose()


def _validate_action(action: str) -> str:
    if action not in ("block", "open"):
        raise HTTPException(status_code=422, detail="action debe ser 'block' u 'open'")
    return action


@router.post("/availability/preview")
async def availability_preview(
    req: AvailabilityPreviewRequest, session: AsyncSession = Depends(get_session)
):
    preview = await availability_service.preview(
        session,
        unit_type_id=req.unit_type_id,
        selection=req.selection.to_selection(),
        action=_validate_action(req.action),
    )
    return asdict(preview)


@router.post("/availability/apply")
async def availability_apply(
    req: AvailabilityApplyRequest, session: AsyncSession = Depends(get_session)
):
    adapter = get_adapter()
    try:
        result = await availability_service.apply(
            session,
            adapter,
            unit_type_id=req.unit_type_id,
            selection=req.selection.to_selection(),
            action=_validate_action(req.action),
            fingerprint=req.fingerprint,
        )
        await session.commit()
        return asdict(result)
    finally:
        await adapter.aclose()


@router.post("/rollback")
async def rollback(req: RollbackRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        result = await pricing_app_service.rollback_and_publish(
            session, adapter, req.change_id, confirm=req.confirm
        )
        await session.commit()
        return asdict(result)
    except RollbackConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        await adapter.aclose()


@router.get("/history")
async def get_history(
    unit_type_id: int, date_from: date, date_to: date, session: AsyncSession = Depends(get_session)
):
    logs = await pricing_app_service.history(session, unit_type_id, date_from, date_to)
    return [
        {
            "id": log.id,
            "date": log.date.isoformat(),
            "old_price": str(log.old_price) if log.old_price is not None else None,
            "new_price": str(log.new_price),
            "origin": log.origin.value,
            "changed_at": log.changed_at.isoformat() if log.changed_at else None,
        }
        for log in logs
    ]


@router.get("/promotions")
async def list_promotions(unit_type_id: int, session: AsyncSession = Depends(get_session)):
    promos = await offer_promotion_service.list_promotions(session, unit_type_id)
    return {"promotions": [asdict(p) for p in promos]}


@router.post("/promotions/preview")
async def promotion_preview(
    req: OfferPromoPreviewRequest, session: AsyncSession = Depends(get_session)
):
    adapter = get_adapter()
    try:
        prev = await offer_promotion_service.preview(
            session,
            adapter,
            unit_type_id=req.unit_type_id,
            first_night=req.first_night,
            last_night=req.last_night,
            name=req.name,
            discount_pct=req.discount_pct,
            price=req.price,
            min_nights=req.min_nights,
            exclude_id=req.promotion_id,
            channels_scope=req.channels_scope,
        )
        return asdict(prev)
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await adapter.aclose()


@router.post("/promotions/apply")
async def promotion_apply(
    req: OfferPromoApplyRequest, session: AsyncSession = Depends(get_session)
):
    adapter = get_adapter()
    try:
        result = await offer_promotion_service.apply(
            session,
            adapter,
            unit_type_id=req.unit_type_id,
            first_night=req.first_night,
            last_night=req.last_night,
            name=req.name,
            discount_pct=req.discount_pct,
            price=req.price,
            min_nights=req.min_nights,
            promotion_id=req.promotion_id,
            fingerprint=req.fingerprint,
            confirm_overlap=req.confirm_overlap,
            channels_scope=req.channels_scope,
        )
        await session.commit()
        return asdict(result)
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await adapter.aclose()


@router.post("/promotions/retire")
async def promotion_retire(
    req: OfferPromoRetireRequest, session: AsyncSession = Depends(get_session)
):
    adapter = get_adapter()
    try:
        result = await offer_promotion_service.retire(
            session, adapter, req.id, confirm=req.confirm
        )
        await session.commit()
        return asdict(result)
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await adapter.aclose()


@router.get("/channel-offsets")
async def get_channel_offsets(session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        offsets = await channel_pricing_service.get_offsets(session, adapter)
        return {"offsets": offsets}
    finally:
        await adapter.aclose()


@router.post("/channel-offsets/preview")
async def channel_offset_preview(
    req: ChannelOffsetPreviewRequest, session: AsyncSession = Depends(get_session)
):
    adapter = get_adapter()
    try:
        return await channel_pricing_service.preview_offset(
            session, adapter, req.channel, req.offset_pct
        )
    except ChannelOffsetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await adapter.aclose()


@router.post("/channel-offsets/apply")
async def channel_offset_apply(
    req: ChannelOffsetApplyRequest, session: AsyncSession = Depends(get_session)
):
    adapter = get_adapter()
    try:
        result = await channel_pricing_service.apply_offset(
            session,
            adapter,
            req.channel,
            req.offset_pct,
            fingerprint=req.fingerprint,
            origin=ChangeOrigin.manual,
        )
        await session.commit()
        return result
    except FingerprintError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ChannelOffsetError as exc:
        await session.commit()  # persistir la SyncIssue del fallo
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await adapter.aclose()


@router.post("/promotions/legacy")
async def create_promotion(req: PromotionRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        promo = await promotion_service.create_promotion(
            session,
            adapter,
            property_id=req.property_id,
            name=req.name,
            discount_type=req.discount_type,
            discount_value=req.discount_value,
            start_date=req.start_date,
            end_date=req.end_date,
            conditions=req.conditions,
        )
        await session.commit()
        return {"id": promo.id, "name": promo.name, "status": promo.status.value}
    finally:
        await adapter.aclose()


@router.delete("/promotions/{promotion_id}")
async def delete_promotion(promotion_id: int, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        await promotion_service.delete_promotion(session, adapter, promotion_id)
        await session.commit()
        return {"deleted": promotion_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        await adapter.aclose()


# --------- Extender precios hacia el futuro (feature 023) ---------


class ExtensionMonthBody(BaseModel):
    month: str
    price: Decimal | None = None
    included: bool = True


class ExtensionPreviewRequest(BaseModel):
    unit_type_id: int
    until: date | None = None
    weekend_pct: Decimal = Decimal(0)
    open_closed: bool = True
    months: list[ExtensionMonthBody] | None = None

    def to_params(self) -> ExtensionParams:
        return ExtensionParams(
            unit_type_id=self.unit_type_id,
            until=self.until,
            weekend_pct=self.weekend_pct,
            open_closed=self.open_closed,
            months=(
                [MonthInput(m.month, m.price, m.included) for m in self.months]
                if self.months is not None
                else None
            ),
        )


class ExtensionApplyRequest(ExtensionPreviewRequest):
    fingerprint: str


def _preview_json(p) -> dict:
    data = asdict(p)
    for m in data["months"]:
        m.pop("items", None)  # el detalle por noche no viaja (hasta ~700 noches)
    return data


@router.get("/extension/status")
async def extension_status(unit_type_id: int, session: AsyncSession = Depends(get_session)):
    return asdict(
        await price_extension_service.status(session, unit_type_id, today=date.today())
    )


@router.post("/extension/preview")
async def extension_preview(
    req: ExtensionPreviewRequest, session: AsyncSession = Depends(get_session)
):
    adapter = get_adapter()
    try:
        preview = await price_extension_service.preview(
            session, adapter, req.to_params(), today=date.today()
        )
        return _preview_json(preview)
    except ExtensionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ChannelError as exc:
        raise HTTPException(
            status_code=502, detail=f"no se pudo leer el Channel Manager: {exc}"
        ) from exc
    finally:
        await adapter.aclose()


@router.post("/extension/apply")
async def extension_apply(req: ExtensionApplyRequest, session: AsyncSession = Depends(get_session)):
    adapter = get_adapter()
    try:
        result = await price_extension_service.apply(
            session,
            adapter,
            req.to_params(),
            req.fingerprint,
            today=date.today(),
            on_month_done=session.commit,  # cada mes publicado queda guardado
        )
        if result.stale:
            raise HTTPException(
                status_code=409,
                detail="la vista previa quedó desactualizada; vuelve a previsualizar",
            )
        await session.commit()
        return asdict(result)
    except ExtensionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ChannelError as exc:
        raise HTTPException(
            status_code=502, detail=f"no se pudo leer el Channel Manager: {exc}"
        ) from exc
    finally:
        await adapter.aclose()
