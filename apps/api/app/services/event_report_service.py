"""Consultar y reportar eventos (feature 035, "¿Falta un evento?").

El anfitrión conoce su zona mejor que cualquier buscador. Puede reportar un evento que falta;
StayLever lo verifica con UNA búsqueda antes de compartirlo con las demás cuentas del área:

- Ya existe (nombre parecido el mismo día en su área) → `exists`, sin costo.
- Se confirma en la web → `verified`: pasa a la tabla pública `event` y se recalculan las
  sugerencias de esas fechas de su cuenta (no se aplica nada: el anfitrión aprueba).
- No se confirma → `unverified`: nota privada en su calendario; no afecta a nadie más.

Tope: 3 reportes al día por cuenta; el costo de la búsqueda y de la IA va a `ai_usage` (027),
aparte del tope diario de búsquedas del escaneo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import municipalities
from app.models.enums import EventKind, Relevance
from app.models.market import Event, EventReport
from app.models.mixins import _now
from app.models.property import UnitType
from app.services import calendar_note_service, event_service, intelligence_service

REPORTS_PER_DAY = 3
MAX_DAYS = 31
HORIZON_DAYS = 400
MAX_LIST = 60
EXISTS, VERIFIED, UNVERIFIED = "exists", "verified", "unverified"


class ReportError(ValueError):
    pass


@dataclass
class ReportResult:
    status: str
    event: dict | None = None
    message: str = ""


def _event_dict(e: Event) -> dict:
    origin = ("festivo" if e.kind is EventKind.holiday
              else "boletera" if e.source_url else "búsqueda")
    return {
        "name": e.name,
        "start_date": e.start_date.isoformat(),
        "end_date": (e.end_date or e.start_date).isoformat(),
        "venue": e.location,
        "city": e.city,
        "relevance": e.relevance.value,
        "kind": e.kind.value,
        "origin": origin,
    }


async def _area(session: AsyncSession) -> tuple[str, list[str]]:
    city = await intelligence_service.property_city(session)
    return city, municipalities.area_keys(city)


async def list_events(session: AsyncSession, date_from: date, date_to: date) -> list[dict]:
    """Eventos ya guardados del área de la propiedad (sin costo de búsqueda)."""
    _, keys = await _area(session)
    rows = (
        await session.execute(
            select(Event)
            .where(Event.city.in_(keys), Event.start_date <= date_to,
                   func.coalesce(Event.end_date, Event.start_date) >= date_from)
            .order_by(Event.start_date)
        )
    ).scalars().all()
    rows = event_service.unique_events(rows)[:MAX_LIST]
    reported = {
        (r.event_id) for r in (await session.execute(
            select(EventReport).where(EventReport.status == VERIFIED))).scalars()
    }
    out = []
    for e in rows:
        d = _event_dict(e)
        if e.id in reported:
            d["origin"] = "reportado por ti"
        out.append(d)
    return out


async def reports_today(session: AsyncSession) -> int:
    since = _now() - timedelta(hours=24)
    return (
        await session.execute(
            select(func.count()).select_from(EventReport).where(
                EventReport.created_at >= since, EventReport.status != EXISTS)
        )
    ).scalar_one()


def _validate(name: str, start: date, end: date | None, today: date) -> tuple[str, date | None]:
    name = " ".join((name or "").split())
    if not 3 <= len(name) <= 200:
        raise ReportError("Escribe el nombre del evento (3 a 200 caracteres).")
    if start < today or start > today + timedelta(days=HORIZON_DAYS):
        raise ReportError("La fecha debe estar entre hoy y los próximos 13 meses.")
    if end is not None:
        if end < start or (end - start).days > MAX_DAYS:
            raise ReportError("Revisa las fechas: el fin va después del inicio (máx. 31 días).")
        if end == start:
            end = None
    return name, end


def _human_date(d: date) -> str:
    months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
              "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{d.day} de {months[d.month - 1]} de {d.year}"


async def _verify(name: str, start: date, venue: str | None, city: str, search, llm,
                  today: date):
    """Una búsqueda + una extracción: ¿algún resultado trae ese evento en esa fecha?"""
    from app.market.extractor import extract_events

    query = " ".join(x for x in (name, venue, city, _human_date(start)) if x)
    try:
        results = await search.search(query, max_results=8)
    except Exception:  # noqa: BLE001 — sin búsqueda no se puede confirmar
        return None, None
    for cand in await extract_events(llm, results, city, today):
        if cand.start_date == start and event_service.similar_names(cand.name, name):
            url = next((r.url for r in results if r.url and event_service.similar_names(
                name, r.title or "")), None) or next((r.url for r in results if r.url), None)
            return cand, url
    return None, None


async def report(
    session: AsyncSession, *, name: str, start_date: date, end_date: date | None = None,
    venue: str | None = None, search=None, llm=None, today: date | None = None,
) -> ReportResult:
    from app.services import event_sources_service as sources

    today = today or date.today()
    name, end_date = _validate(name, start_date, end_date, today)
    venue = (" ".join((venue or "").split()) or None)
    venue = venue[:200] if venue else None
    city, keys = await _area(session)

    existing = await event_service._similar(session, keys, start_date, name)
    if existing is not None:
        session.add(EventReport(name=name, start_date=start_date, end_date=end_date, venue=venue,
                                status=EXISTS, event_id=existing.id))
        await session.commit()
        return ReportResult(EXISTS, _event_dict(existing),
                            "Ese evento ya lo teníamos; ya cuenta en tus sugerencias.")

    if await reports_today(session) >= REPORTS_PER_DAY:
        raise ReportError(f"Llegaste al tope de {REPORTS_PER_DAY} reportes por día. "
                          "Inténtalo mañana.")

    cand, url = (None, None)
    if search is not None and llm is not None:
        cand, url = await _verify(name, start_date, venue, city, search, llm, today)

    if cand is not None:
        v = sources.venue_for(venue or cand.location)
        m = municipalities.get(v["municipality"]) if v else None
        ev_city = m.city_key if m else event_service.normalize_city(city)
        relevance = Relevance.high if v and v["capacity"] >= 10000 else (
            Relevance.medium if v and v["capacity"] >= 3000 else cand.relevance)
        ev = await event_service.upsert_structured(
            session, name=name, start_date=start_date, end_date=end_date or cand.end_date,
            kind=cand.kind, relevance=relevance, location=(v["name"] if v else venue or cand.location),
            source_url=url or f"reportado:{name}:{start_date.isoformat()}", city=ev_city,
            area=keys,
        )
        session.add(EventReport(name=name, start_date=start_date, end_date=end_date,
                                venue=venue, status=VERIFIED, event_id=ev.id))
        await session.flush()
        await _regenerate(session, start_date, end_date or start_date, today)
        await session.commit()
        return ReportResult(VERIFIED, _event_dict(ev),
                            "¡Confirmado! Lo agregamos y recalculamos tus sugerencias de esas "
                            "fechas. Revísalas en Sugerencias.")

    unit = (await session.execute(select(UnitType).order_by(UnitType.id))).scalars().first()
    if unit is not None:
        text = f"Evento reportado sin confirmar: {name}" + (f" ({venue})" if venue else "")
        await calendar_note_service.create(
            session, unit_type_id=unit.id, date_from=start_date,
            date_to=end_date or start_date, text=text[:500],
        )
    session.add(EventReport(name=name, start_date=start_date, end_date=end_date, venue=venue,
                            status=UNVERIFIED))
    await session.commit()
    return ReportResult(UNVERIFIED, None,
                        "No pudimos confirmarlo en la web. Lo dejamos como nota en tu "
                        "calendario para que lo tengas en cuenta al fijar el precio.")


async def _regenerate(session: AsyncSession, first: date, last: date, today: date) -> None:
    from app.services import suggestion_engine

    for unit in (await session.execute(select(UnitType))).scalars().all():
        await suggestion_engine.generate_suggestions(
            session, unit_type_id=unit.id, date_from=max(first, today), date_to=last,
            market=None, today=today,
        )


def search_provider():
    from app.services.secret_service import get_secret

    if not get_secret("search_api_key"):
        return None
    from app.search.tavily import TavilyProvider

    return TavilyProvider()


async def report_metered(session: AsyncSession, **kw) -> ReportResult:
    """Reporte con la búsqueda y la IA reales, medidas en el uso de la cuenta (027).

    La búsqueda no consume el tope diario del escaneo: el tope propio son 3 reportes al día.
    """
    from app.llm.client import default_llm
    from app.services import usage_service

    raw = search_provider()
    llm = default_llm()
    search = usage_service.MeteredSearch(raw, session, limit=10**6) if raw else None
    metered_llm = usage_service.MeteredLLM(llm, session, usage_service.CHAT) if llm else None
    try:
        return await report(session, search=search, llm=metered_llm, **kw)
    finally:
        if raw is not None and hasattr(raw, "aclose"):
            await raw.aclose()
