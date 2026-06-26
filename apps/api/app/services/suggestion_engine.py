"""Genera PriceSuggestion por día combinando evento + ocupación + mercado (heurística pura)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.suggestion import suggest_price
from app.models.calendar import CalendarDay
from app.models.enums import Relevance, SuggestionStatus
from app.models.market import Event, PriceSuggestion
from app.models.property import Property, UnitType
from app.services import pricing_service

_REL_ORDER = {Relevance.low: 0, Relevance.medium: 1, Relevance.high: 2}
_REPROPOSE_BLOCK = (
    SuggestionStatus.proposed,
    SuggestionStatus.approved,
    SuggestionStatus.applied,
    SuggestionStatus.rejected,
)


async def _event_relevance(session: AsyncSession, day: date) -> Relevance | None:
    res = await session.execute(select(Event).where(Event.start_date <= day))
    best: Relevance | None = None
    for ev in res.scalars():
        end = ev.end_date or ev.start_date
        if ev.start_date <= day <= end:
            if best is None or _REL_ORDER[ev.relevance] > _REL_ORDER[best]:
                best = ev.relevance
    return best


async def _occupancy_high(session: AsyncSession, unit_type_id: int, day: date) -> bool:
    res = await session.execute(
        select(CalendarDay.units_available).where(
            CalendarDay.unit_type_id == unit_type_id, CalendarDay.date == day
        )
    )
    val = res.scalar_one_or_none()
    return val is not None and val == 0


async def _exists_equivalent(
    session: AsyncSession, unit_type_id: int, day: date, price: Decimal
) -> bool:
    res = await session.execute(
        select(PriceSuggestion).where(
            PriceSuggestion.unit_type_id == unit_type_id,
            PriceSuggestion.date_from == day,
            PriceSuggestion.suggested_price == price,
            PriceSuggestion.status.in_(_REPROPOSE_BLOCK),
        )
    )
    return res.scalars().first() is not None


async def generate_suggestions(
    session: AsyncSession,
    *,
    unit_type_id: int,
    date_from: date,
    date_to: date,
    market=None,
) -> list[PriceSuggestion]:
    unit = await session.get(UnitType, unit_type_id)
    prop = await session.get(Property, unit.property_id)
    zone = prop.city
    rule = await pricing_service.get_active_rule(session, prop.id)
    min_p = rule.min_price if rule else None
    max_p = rule.max_price if rule else None

    created: list[PriceSuggestion] = []
    day = date_from
    while day <= date_to:
        base = await pricing_service.get_price(session, unit_type_id, day)
        if base is not None:
            relevance = await _event_relevance(session, day)
            occ_high = await _occupancy_high(session, unit_type_id, day)
            mref = await market.get(zone, day) if market is not None else None
            out = suggest_price(
                base,
                event_relevance=relevance,
                occupancy_high=occ_high,
                market_ref=mref,
                min_price=min_p,
                max_price=max_p,
            )
            if out is not None and not await _exists_equivalent(
                session, unit_type_id, day, out.price
            ):
                sug = PriceSuggestion(
                    property_id=prop.id,
                    unit_type_id=unit_type_id,
                    date_from=day,
                    date_to=day,
                    suggested_price=out.price,
                    rationale={
                        "text": out.justification,
                        "event_relevance": relevance.value if relevance else None,
                    },
                    confidence=out.confidence,
                    status=SuggestionStatus.proposed,
                )
                session.add(sug)
                created.append(sug)
        day += timedelta(days=1)
    await session.flush()
    return created
