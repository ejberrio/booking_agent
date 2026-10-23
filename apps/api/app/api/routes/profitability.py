"""Rentabilidad mensual de una unidad frente a un arriendo tradicional (feature 042)."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services import profitability_service

router = APIRouter()


@router.get("")
async def get_profitability(
    unit_type_id: int,
    months_back: int = Query(default=12, ge=1, le=24),
    months_ahead: int = Query(default=3, ge=0, le=12),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await profitability_service.report(
            session, unit_type_id, months_back=months_back, months_ahead=months_ahead
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


class SettingsIn(BaseModel):
    unit_type_id: int
    reference_rent: Decimal | None = Field(default=None, ge=0, le=10**10)
    fixed_costs: Decimal | None = Field(default=None, ge=0, le=10**10)
    cleaning_per_stay: Decimal | None = Field(default=None, ge=0, le=10**9)


@router.put("/settings")
async def save_profitability_settings(req: SettingsIn, session: AsyncSession = Depends(get_session)):
    await profitability_service.save_settings(
        session, req.unit_type_id, reference_rent=req.reference_rent,
        fixed_costs=req.fixed_costs, cleaning_per_stay=req.cleaning_per_stay,
    )
    await session.commit()
    return await profitability_service.report(session, req.unit_type_id)
