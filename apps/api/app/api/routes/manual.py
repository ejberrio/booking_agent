"""Modo sin conexión (feature 029): apartamento a mano y calendarios iCal."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, require_ctx
from app.db.session import get_session
from app.models.account import Account
from app.models.enums import ChannelKind
from app.services import ical_service, manual_service
from app.services.manual_service import ManualError, ManualListing

router = APIRouter()


class ListingsIn(BaseModel):
    airbnb_url: str | None = Field(default=None, max_length=500)
    airbnb_ical: str | None = Field(default=None, max_length=1000)
    booking_url: str | None = Field(default=None, max_length=500)
    booking_ical: str | None = Field(default=None, max_length=1000)

    def listings(self) -> list[ManualListing]:
        out = []
        if self.airbnb_url or self.airbnb_ical:
            out.append(ManualListing(ChannelKind.airbnb, self.airbnb_url, self.airbnb_ical))
        if self.booking_url or self.booking_ical:
            out.append(ManualListing(ChannelKind.booking, self.booking_url, self.booking_ical))
        return out


class ApartmentIn(ListingsIn):
    name: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=120)
    currency: str = Field(default="COP", min_length=3, max_length=3)
    weekday_price: Decimal = Field(gt=0)
    weekend_price: Decimal | None = Field(default=None, gt=0)


def _report(r: ical_service.SyncReport) -> dict:
    return {"channels": r.channels, "bookings": r.bookings, "cancelled": r.cancelled,
            "blocked_nights": r.blocked_nights, "errors": r.errors}


@router.get("")
async def manual_overview(
    session: AsyncSession = Depends(get_session), ctx: RequestContext = Depends(require_ctx)
):
    acc = await session.get(Account, ctx.account_id)
    return {"channel_mode": acc.channel_mode if acc else "connected",
            "apartments": await manual_service.overview(session)}


@router.post("/apartments")
async def create_apartment(
    req: ApartmentIn,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_ctx),
):
    try:
        unit = await manual_service.create_apartment(
            session, ctx.account_id, name=req.name, city=req.city, currency=req.currency,
            weekday_price=req.weekday_price, weekend_price=req.weekend_price,
            listings=req.listings(),
        )
    except ManualError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    report = await ical_service.sync_account(session)
    await session.commit()
    return {"unit_type_id": unit.id, "ical": _report(report)}


@router.patch("/apartments/{property_id}/listings")
async def update_listings(
    property_id: int,
    req: ListingsIn,
    session: AsyncSession = Depends(get_session),
):
    try:
        await manual_service.update_listings(session, property_id, req.listings())
    except ManualError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    report = await ical_service.sync_account(session)
    await session.commit()
    return {"apartments": await manual_service.overview(session), "ical": _report(report)}


@router.post("/ical/sync")
async def sync_ical(session: AsyncSession = Depends(get_session)):
    report = await ical_service.sync_account(session)
    await session.commit()
    return _report(report)
