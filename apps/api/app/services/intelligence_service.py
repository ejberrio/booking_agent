"""Orquestación del escaneo (eventos + mercado → sugerencias) y aplicación de sugerencias."""

from __future__ import annotations

from datetime import date, timedelta

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
    pricing_service,
    suggestion_engine,
    suggestion_service,
)


async def get_or_create_scan_config(session: AsyncSession):
    """Fila única de configuración del scan (feature 018), autocreada con defaults."""
    from app.models.intelligence import ScanConfig

    cfg = (await session.execute(select(ScanConfig))).scalars().first()
    if cfg is None:
        cfg = ScanConfig()
        session.add(cfg)
        await session.flush()
    return cfg


async def property_city(session: AsyncSession) -> str:
    """Ciudad de la (primera) propiedad de la cuenta (feature 026; antes Medellín fijo)."""
    from app.models.property import Property

    prop = (await session.execute(select(Property).order_by(Property.id))).scalars().first()
    return (prop.city if prop and prop.city else None) or event_service.DEFAULT_CITY


async def effective_zone(session: AsyncSession, cfg) -> str:
    """Zona de búsqueda: override de config, o city+address de la propiedad."""
    from app.models.property import Property

    if cfg.zone:
        return cfg.zone
    prop = (await session.execute(select(Property).order_by(Property.id))).scalars().first()
    if prop is None:
        return event_service.DEFAULT_CITY
    return ", ".join(p for p in (prop.city, prop.address) if p)


async def build_scan_queries(
    session: AsyncSession, today: date, *, include_city_queries: bool = True
) -> tuple[list[str], dict]:
    """Consultas dirigidas del scan: zona + POIs activos/vigentes + tipos de evento.

    Respeta el presupuesto (queries_per_scan) y reporta qué se usó (detail del run).
    `include_city_queries=False` (feature 026): la ciudad ya se escaneó en esta corrida
    para otra cuenta; solo quedan las consultas de los POIs propios.
    """
    from app.models.market import PointOfInterest

    cfg = await get_or_create_scan_config(session)
    zone = await effective_zone(session, cfg)
    kinds = cfg.event_kinds or "conciertos ferias convenciones festivales"

    queries = (
        [
            f"eventos {kinds} {zone} este mes y próximos meses",
            f"eventos importantes agenda {zone}",
        ]
        if include_city_queries
        else []
    )
    pois = [
        p
        for p in (await session.execute(select(PointOfInterest))).scalars()
        if p.is_active and (p.date_to is None or p.date_to >= today)
    ]
    for poi in pois:
        when = ""
        if poi.date_from:
            when = f" {poi.date_from.isoformat()[:7]}"
        queries.append(f"eventos {kinds} {poi.name} {zone}{when}")

    budget = cfg.queries_per_scan
    detail = {
        "zone": zone,
        "pois": [p.name for p in pois],
        "queries_built": len(queries),
        "budget": budget,
        "truncated": len(queries) > budget,
    }
    return queries[:budget], detail


async def scan_events(
    session: AsyncSession, search, llm, *, queries: list[str], city: str | None = None
) -> int:
    city = city or await property_city(session)
    found = 0
    for query in queries:
        results = await search.search(query)
        for cand in await extract_events(llm, results, city):
            await event_service.upsert_event(
                session,
                name=cand.name,
                start_date=cand.start_date,
                kind=cand.kind,
                end_date=cand.end_date,
                relevance=cand.relevance,
                location=cand.location,
                city=city,
            )
            found += 1
    return found


async def scan(
    session: AsyncSession,
    search,
    llm,
    market,
    *,
    unit_type_id: int,
    date_from: date,
    date_to: date,
    queries: list[str] | None = None,
    include_city_queries: bool = True,
) -> IntelligenceRun:
    """Corrida completa: eventos (consultas dirigidas) + mercado + sugerencias v2.

    `queries=None` = construirlas desde la configuración del scan (zona + POIs).
    `market` es un MarketDataProvider (o None = sin señal de mercado, honesto).
    """
    run = IntelligenceRun(status=SyncStatus.running)
    session.add(run)
    await session.flush()

    detail: dict = {}
    if queries is None:
        queries, detail = await build_scan_queries(
            session, date_from, include_city_queries=include_city_queries
        )

    run.events_found = await scan_events(session, search, llm, queries=queries)
    suggestions = await suggestion_engine.generate_suggestions(
        session, unit_type_id=unit_type_id, date_from=date_from, date_to=date_to, market=market
    )
    run.suggestions_created = len(suggestions)
    run.status = SyncStatus.success
    run.finished_at = _now()
    if detail:
        import json

        run.detail = json.dumps(detail, ensure_ascii=False)
    await session.flush()
    return run


class SuggestionStateError(ValueError):
    """Conflicto de estado o vigencia: la acción no procede y no tuvo efectos."""


class SuggestionPublishError(RuntimeError):
    """La publicación al canal falló por completo: nada debe quedar aplicado."""


async def approve(session: AsyncSession, suggestion_id: int) -> PriceSuggestion:
    return await suggestion_service.approve(session, suggestion_id)


async def reject(session: AsyncSession, suggestion_id: int) -> PriceSuggestion:
    return await suggestion_service.reject(session, suggestion_id)


async def apply_suggestion(
    session: AsyncSession, channel, suggestion_id: int, *, today: date | None = None
) -> tuple[PriceSuggestion, date, int]:
    """Acción única "Aprobar y aplicar": valida → aplica (solo días no pasados) → publica → audita.

    Devuelve (sugerencia, applied_from, publish_issues). Las noches pasadas nunca
    se tocan; si la publicación falla por completo se lanza SuggestionPublishError
    ANTES de marcarla aplicada (sin commit no queda nada persistido).
    """
    sug = await session.get(PriceSuggestion, suggestion_id)
    if sug is None:
        raise LookupError(f"No existe la sugerencia {suggestion_id}")
    if sug.status not in (SuggestionStatus.proposed, SuggestionStatus.approved):
        raise SuggestionStateError(
            f"La sugerencia ya está resuelta (estado real: {sug.status.value})"
        )
    if sug.unit_type_id is None:
        raise SuggestionStateError("La sugerencia no tiene unidad asignada")

    today = today or date.today()
    if sug.date_to < today:
        raise SuggestionStateError(
            f"La sugerencia venció (rango {sug.date_from} → {sug.date_to}, todo en el pasado)"
        )
    applied_from = max(sug.date_from, today)

    # Feature 022: una bajada NUNCA baja el precio base; se aplica como promoción desde
    # la vista previa del lote (/suggestions/batch/*), que respeta el precio mínimo.
    current = await pricing_service.get_price(session, sug.unit_type_id, applied_from)
    if current is not None and sug.suggested_price < current:
        raise SuggestionStateError(
            "Las bajadas se aplican como promoción desde la vista previa del lote"
        )

    applied = issues = 0
    day = applied_from
    while day <= sug.date_to:
        result = await pricing_app_service.set_day_price(
            session,
            channel,
            unit_type_id=sug.unit_type_id,
            day=day,
            price=sug.suggested_price,
            origin=ChangeOrigin.suggestion,
        )
        applied += len(result.applied_days)
        issues += result.publish_issues
        day += timedelta(days=1)

    if applied == 0:
        raise SuggestionStateError(
            "El precio sugerido viola la regla de precios vigente; no se aplicó nada"
        )
    if issues > 0:
        # El precio de la sugerencia es uniforme (un solo grupo por día): cualquier
        # incidencia significa que ese día no llegó al canal.
        raise SuggestionPublishError(
            "no se pudo publicar el precio al canal; la sugerencia sigue pendiente"
        )

    res = await session.execute(
        select(PriceChangeLog.id)
        .where(
            PriceChangeLog.unit_type_id == sug.unit_type_id,
            PriceChangeLog.date == applied_from,
        )
        .order_by(PriceChangeLog.id.desc())
    )
    sug.applied_change_id = res.scalars().first()
    sug.status = SuggestionStatus.applied
    await session.flush()
    return sug, applied_from, issues


async def list_suggestions(
    session: AsyncSession,
    *,
    status: SuggestionStatus | None = None,
    statuses: list[SuggestionStatus] | None = None,
) -> list[PriceSuggestion]:
    stmt = select(PriceSuggestion).order_by(PriceSuggestion.date_from)
    if statuses is not None:
        stmt = stmt.where(PriceSuggestion.status.in_(statuses))
    elif status is not None:
        stmt = stmt.where(PriceSuggestion.status == status)
    res = await session.execute(stmt)
    return list(res.scalars())
