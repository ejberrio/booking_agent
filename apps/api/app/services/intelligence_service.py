"""Orquestación del escaneo (eventos + mercado → sugerencias) y aplicación de sugerencias."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.market.extractor import extract_events
from app.models.audit import PriceChangeLog
from app.models.enums import ChangeOrigin, SuggestionStatus, SyncStatus
from app.models.intelligence import IntelligenceRun
from app.models.market import PriceSuggestion
from app.models.mixins import _now
from app.services import (
    event_service,
    pricing_app_service,
    suggestion_engine,
    suggestion_service,
)


async def scan_events(session: AsyncSession, search, llm, *, queries: list[str]) -> int:
    found = 0
    for query in queries:
        results = await search.search(query)
        for cand in await extract_events(llm, results):
            await event_service.upsert_event(
                session,
                name=cand.name,
                start_date=cand.start_date,
                kind=cand.kind,
                end_date=cand.end_date,
                relevance=cand.relevance,
                location=cand.location,
            )
            found += 1
    return found


async def scan(
    session: AsyncSession,
    search,
    llm,
    market,
    *,
    queries: list[str],
    unit_type_id: int,
    date_from: date,
    date_to: date,
) -> IntelligenceRun:
    run = IntelligenceRun(status=SyncStatus.running)
    session.add(run)
    await session.flush()

    run.events_found = await scan_events(session, search, llm, queries=queries)
    suggestions = await suggestion_engine.generate_suggestions(
        session, unit_type_id=unit_type_id, date_from=date_from, date_to=date_to, market=market
    )
    run.suggestions_created = len(suggestions)
    run.status = SyncStatus.success
    run.finished_at = _now()
    await session.flush()
    return run


async def approve(session: AsyncSession, suggestion_id: int) -> PriceSuggestion:
    return await suggestion_service.approve(session, suggestion_id)


async def reject(session: AsyncSession, suggestion_id: int) -> PriceSuggestion:
    return await suggestion_service.reject(session, suggestion_id)


async def apply_suggestion(session: AsyncSession, channel, suggestion_id: int) -> PriceSuggestion:
    """Aplica una sugerencia vía el motor de precios (origen=sugerencia): audita + publica."""
    sug = await session.get(PriceSuggestion, suggestion_id)
    if sug is None:
        raise ValueError(f"No existe la sugerencia {suggestion_id}")
    if sug.unit_type_id is None:
        raise ValueError("La sugerencia no tiene unidad asignada")

    from datetime import timedelta

    day = sug.date_from
    while day <= sug.date_to:
        await pricing_app_service.set_day_price(
            session,
            channel,
            unit_type_id=sug.unit_type_id,
            day=day,
            price=sug.suggested_price,
            origin=ChangeOrigin.suggestion,
        )
        day += timedelta(days=1)

    res = await session.execute(
        select(PriceChangeLog.id)
        .where(
            PriceChangeLog.unit_type_id == sug.unit_type_id,
            PriceChangeLog.date == sug.date_from,
        )
        .order_by(PriceChangeLog.id.desc())
    )
    sug.applied_change_id = res.scalars().first()
    sug.status = SuggestionStatus.applied
    await session.flush()
    return sug


async def list_suggestions(
    session: AsyncSession, *, status: SuggestionStatus | None = None
) -> list[PriceSuggestion]:
    stmt = select(PriceSuggestion).order_by(PriceSuggestion.date_from)
    if status is not None:
        stmt = stmt.where(PriceSuggestion.status == status)
    res = await session.execute(stmt)
    return list(res.scalars())
