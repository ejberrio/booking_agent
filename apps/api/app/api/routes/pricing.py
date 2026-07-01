from dataclasses import asdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.sync import get_adapter
from app.db.session import get_session
from app.models.enums import PromotionType
from app.schemas.pricing import RangeSelection
from app.services import (
    availability_service,
    offer_promotion_service,
    pricing_app_service,
    promotion_service,
)
from app.services.audit_service import RollbackConflict
from app.services.offer_promotion_service import PromotionError

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


class OfferPromoApplyRequest(OfferPromoPreviewRequest):
    fingerprint: str
    confirm_overlap: bool = False


class OfferPromoRetireRequest(BaseModel):
    id: int
    confirm: bool = True


@router.get("/calendar")
async def calendar(
    unit_type_id: int, date_from: date, date_to: date, session: AsyncSession = Depends(get_session)
):
    views = await pricing_app_service.get_calendar(session, unit_type_id, date_from, date_to)
    return [asdict(v) for v in views]


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
