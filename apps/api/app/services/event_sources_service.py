"""Fuentes estructuradas de eventos (feature 034): boleteras y agendas que publican sus
eventos en formatos legibles por programas, más festivos y puentes.

Por qué: las búsquedas genéricas ("agenda de Medellín") no encuentran conciertos como Hebert
Vargas en la DAVIarena (4-dic-2026), que solo están en la boletera. Aquí se leen, sin IA:

- **TuBoleta**: resultados por ciudad + ficha de cada evento con JSON-LD `schema.org/Event`.
- **Ticketmaster Colombia** (antes Eticket): página por ciudad + JSON-LD de cada evento.
- **Plaza Mayor** (Medellín): API pública de su agenda (The Events Calendar).
- **Festivos y puentes**: calculados (`app/domain/holidays_co.py`), clave nacional.

Reglas (memorando legal de oct-2026, docs/research/): solo fuentes cuyos términos no prohíben
el acceso automatizado, respetando robots.txt, sin evadir bloqueos ni captchas, despacio
(una petición cada ~1,5 s), con un User-Agent identificable, una vez por semana por ciudad y
guardando solo hechos públicos del evento (nombre, fechas, recinto, municipio, enlace).
Cada fuente se puede apagar (`EVENT_SOURCES_DISABLED`).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain import holidays_co, municipalities
from app.models.enums import EventKind, Relevance
from app.services import event_service

log = logging.getLogger(__name__)

USER_AGENT = "StayLeverBot/1.0 (+https://staylever.com; hello@staylever.com)"
DELAY_S = 1.5
TIMEOUT_S = 20
MAX_PAGES = 6
MAX_EVENTS_PER_RUN = 80
REFRESH_DAYS = 7
HORIZON_DAYS = 400
TZ = ZoneInfo("America/Bogota")

TUBOLETA, TICKETMASTER, PLAZA_MAYOR, HOLIDAYS = "tuboleta", "ticketmaster", "plazamayor", "festivos"
ALLOWED_HOSTS = {
    TUBOLETA: ("tuboleta.com",),
    TICKETMASTER: ("ticketmaster.co",),
    PLAZA_MAYOR: ("plazamayor.com.co",),
}
# Ciudad principal (clave de `event.city`) → identificador de cada fuente.
TUBOLETA_CITIES = {"medellin": 12030, "bogota": 12012, "cali": 14227, "cartagena": 22075,
                   "barranquilla": 12024}
TUBOLETA_VENUES = {"medellin": ["daviarena"]}
TICKETMASTER_CITIES = {"medellin": "medellin", "bogota": "bogota", "cali": "cali",
                       "bucaramanga": "bucaramanga"}
PLAZA_MAYOR_CITIES = {"medellin"}

_DATA = Path(__file__).resolve().parent.parent / "data" / "venues_co.json"


# --------- recintos ---------


@lru_cache(maxsize=1)
def _venues() -> list[dict]:
    return json.loads(_DATA.read_text(encoding="utf-8"))


def venue_for(name: str | None) -> dict | None:
    key = event_service.name_key(name or "")
    if not key:
        return None
    for v in _venues():
        if any(a in key for a in v["aliases"]):
            return v
    return None


# --------- modelo y parseo ---------


@dataclass
class StructuredEvent:
    name: str
    start: date
    end: date | None
    url: str
    venue: str | None = None
    locality: str | None = None
    kind: EventKind = EventKind.other
    cancelled: bool = False
    music: bool = False


def _local_date(value: str | None) -> date | None:
    if not value:
        return None
    v = value.strip()
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
        return date.fromisoformat(m.group(1)) if m else None
    return dt.astimezone(TZ).date() if dt.tzinfo else dt.date()


_KINDS = {
    "musicevent": EventKind.concert,
    "festival": EventKind.festival,
    "exhibitionevent": EventKind.fair,
    "businessevent": EventKind.convention,
    "educationevent": EventKind.convention,
}


def _kind(types, name: str) -> tuple[EventKind, bool]:
    ts = [t.lower() for t in (types if isinstance(types, list) else [types]) if isinstance(t, str)]
    for t in ts:
        if t in _KINDS:
            return _KINDS[t], t == "musicevent"
    n = event_service.name_key(name)
    if re.search(r"\b(feria|expo\w*|bazar|comic con)\b", n):
        return EventKind.fair, False
    if re.search(r"\b(congreso|congress|cumbre|convencion|summit)\b", n):
        return EventKind.convention, False
    if re.search(r"\b(festival|fest)\b", n):
        return EventKind.festival, True
    if re.search(r"\b(concierto|tour|en vivo|live)\b", n):
        return EventKind.concert, True
    return EventKind.other, False


def _iter_jsonld(html: str):
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I
    ):
        try:
            data = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data])
        for it in items:
            if isinstance(it, dict):
                yield it


def events_from_jsonld(html: str, url: str) -> list[StructuredEvent]:
    out: list[StructuredEvent] = []
    for it in _iter_jsonld(html):
        types = it.get("@type")
        if "event" not in json.dumps(types).lower():
            continue
        name = unescape(str(it.get("name") or "")).strip()
        start = _local_date(it.get("startDate"))
        if not name or start is None:
            continue
        end = _local_date(it.get("endDate"))
        loc = it.get("location") if isinstance(it.get("location"), dict) else {}
        addr = loc.get("address") if isinstance(loc.get("address"), dict) else {}
        kind, music = _kind(types, name)
        out.append(StructuredEvent(
            name=name[:300], start=start, end=end if end and end > start else None,
            url=str(it.get("url") or url)[:500], venue=(loc.get("name") or None),
            locality=(addr.get("addressLocality") or None), kind=kind,
            cancelled="cancel" in str(it.get("eventStatus") or "").lower(), music=music,
        ))
    return out


def tuboleta_links(html: str, base: str = "https://tuboleta.com") -> list[str]:
    links = re.findall(r'href="((?:https://tuboleta\.com)?/es/eventos/[a-z0-9\-]+)"', html)
    return list(dict.fromkeys(urljoin(base, x) for x in links))


def ticketmaster_links(html: str, base: str = "https://www.ticketmaster.co") -> list[str]:
    # En el HTML vienen como "../event/slug" dentro de datos embebidos.
    links = re.findall(r'["\'](?:\.\./|/)event/([a-z0-9\-]+)["\']', html)
    return list(dict.fromkeys(f"{base}/event/{x}" for x in links))


def plaza_mayor_events(payload: dict) -> list[StructuredEvent]:
    out = []
    for e in payload.get("events") or []:
        url = str(e.get("url") or "")
        if "/en/" in url:  # la agenda viene duplicada en inglés
            continue
        name = unescape(re.sub(r"<[^>]+>", "", str(e.get("title") or ""))).strip()
        start = _local_date(str(e.get("start_date") or "")[:10])
        if not name or start is None:
            continue
        end = _local_date(str(e.get("end_date") or "")[:10])
        kind, music = _kind(None, name)
        out.append(StructuredEvent(name=name[:300], start=start,
                                   end=end if end and end > start else None, url=url[:500],
                                   venue="Plaza Mayor", locality="Medellín", kind=kind,
                                   music=music))
    return out


def relevance_for(ev: StructuredEvent) -> Relevance:
    v = venue_for(ev.venue)
    cap = v["capacity"] if v else None
    if cap is not None:
        if cap >= 10000:
            return Relevance.high
        if cap >= 3000:
            return Relevance.medium
        return Relevance.low
    if ev.kind in (EventKind.fair, EventKind.festival) or ev.music:
        return Relevance.medium
    return Relevance.low


def city_key_for(ev: StructuredEvent, default_key: str) -> str:
    """Municipio del evento: el del recinto conocido, el de la dirección o el de la búsqueda."""
    v = venue_for(ev.venue)
    if v:
        m = municipalities.get(v["municipality"])
        if m:
            return m.city_key
    if ev.locality:
        key = event_service.normalize_city(ev.locality)
        if municipalities.by_city_key(key):
            return key
    return default_key


# --------- descarga respetuosa ---------


class Fetcher:
    """GET con User-Agent propio, robots.txt, hosts permitidos y una pausa entre peticiones."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, delay: float = DELAY_S):
        self._client = httpx.AsyncClient(
            timeout=TIMEOUT_S, transport=transport, follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "es-CO,es;q=0.9"},
        )
        self._robots: dict[str, RobotFileParser | None] = {}
        self._delay = delay
        self.requests = 0

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _allowed(url: str, hosts: tuple[str, ...]) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return urlparse(url).scheme == "https" and any(
            host == h or host.endswith("." + h) for h in hosts
        )

    async def _can_fetch(self, url: str) -> bool:
        p = urlparse(url)
        origin = f"{p.scheme}://{p.hostname}"
        if origin not in self._robots:
            rp: RobotFileParser | None = RobotFileParser()
            try:
                r = await self._client.get(origin + "/robots.txt")
                self.requests += 1
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except httpx.HTTPError:
                rp = None  # sin robots legible: no se lee el sitio
            self._robots[origin] = rp
        rp = self._robots[origin]
        return rp is not None and rp.can_fetch(USER_AGENT, url)

    async def get(self, url: str, hosts: tuple[str, ...]) -> str | None:
        if not self._allowed(url, hosts) or not await self._can_fetch(url):
            return None
        if self.requests:
            await asyncio.sleep(self._delay)
        try:
            r = await self._client.get(url)
        except httpx.HTTPError:
            return None
        self.requests += 1
        if r.status_code in (403, 429) or "captcha" in r.text[:5000].lower():
            raise PermissionError(f"{urlparse(url).hostname} bloqueó la lectura ({r.status_code})")
        if r.status_code != 200 or not self._allowed(str(r.url), hosts):
            return None
        return r.text


# --------- guardado ---------


@dataclass
class SourceReport:
    sources: dict[str, int] = field(default_factory=dict)
    saved: int = 0
    cancelled: int = 0
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


async def _save(session: AsyncSession, ev: StructuredEvent, default_key: str,
                report: SourceReport, today: date) -> None:
    if ev.start > today + timedelta(days=HORIZON_DAYS) or (ev.end or ev.start) < today:
        return
    if ev.cancelled:
        report.cancelled += await event_service.delete_by_source(session, ev.url)
        return
    city = city_key_for(ev, default_key)
    v = venue_for(ev.venue)
    await event_service.upsert_structured(
        session, name=ev.name, start_date=ev.start, end_date=ev.end, kind=ev.kind,
        relevance=relevance_for(ev), location=(v["name"] if v else ev.venue),
        source_url=ev.url, city=city, area=municipalities.area_keys(city),
    )
    report.saved += 1


def disabled_sources() -> set[str]:
    return {s.strip().lower() for s in (settings.event_sources_disabled or "").split(",") if s.strip()}


async def _from_listing(session, fetcher: Fetcher, source: str, city: str, pages: list[str],
                        link_fn, report: SourceReport, today: date,
                        extra: list[str] | None = None) -> None:
    """`pages`: listado paginado (se detiene cuando una página no trae enlaces nuevos);
    `extra`: páginas sueltas (carteleras de recintos)."""
    hosts = ALLOWED_HOSTS[source]
    links: list[str] = []
    for page_url in pages:
        html = await fetcher.get(page_url, hosts)
        new = [u for u in link_fn(html or "") if u not in links]
        if not new:
            break
        links += new
    for page_url in extra or []:
        html = await fetcher.get(page_url, hosts)
        links += [u for u in link_fn(html or "") if u not in links]
    count = 0
    for url in links[:MAX_EVENTS_PER_RUN]:
        if await event_service.seen_recently(session, url, days=REFRESH_DAYS):
            continue
        html = await fetcher.get(url, hosts)
        for ev in events_from_jsonld(html or "", url):
            await _save(session, ev, city, report, today)
            count += 1
    report.sources[f"{source}:{city}"] = count


async def refresh_city(session: AsyncSession, city: str, *, today: date | None = None,
                       transport: httpx.AsyncBaseTransport | None = None,
                       delay: float = DELAY_S, force: bool = False) -> SourceReport:
    """Lee las fuentes estructuradas de una ciudad principal (como mucho una vez por semana)."""
    from app.services import public_service

    today = today or date.today()
    report = SourceReport()
    off = disabled_sources()
    if "all" in off:
        report.skipped.append("all")
        return report
    fetcher = Fetcher(transport, delay)
    try:
        plan = []
        if city in TUBOLETA_CITIES:
            cid = TUBOLETA_CITIES[city]
            pages = [f"https://tuboleta.com/es/resultados-de-busqueda?ciudades={cid}&page={p}"
                     for p in range(MAX_PAGES)]
            # Cartelera de recintos grandes del área (la DAVIarena queda en Sabaneta).
            venues = [f"https://tuboleta.com/es/venue/{slug}"
                      for slug in TUBOLETA_VENUES.get(city, [])]
            plan.append((TUBOLETA, pages, tuboleta_links, venues))
        if city in TICKETMASTER_CITIES:
            plan.append((TICKETMASTER,
                         [f"https://www.ticketmaster.co/page/{TICKETMASTER_CITIES[city]}"],
                         ticketmaster_links, []))
        for source, pages, link_fn, extra in plan:
            key = f"src:{source}:{city}"
            if source in off:
                report.skipped.append(source)
                continue
            if not force and await public_service.is_fresh(session, key):
                continue
            try:
                await _from_listing(session, fetcher, source, city, pages, link_fn, report, today,
                                    extra)
                await public_service.mark_scanned(session, key, report.sources.get(f"{source}:{city}", 0))
            except PermissionError as exc:
                report.errors.append(str(exc))  # bloqueados: no se insiste (sin evadir)
        if city in PLAZA_MAYOR_CITIES and PLAZA_MAYOR not in off:
            key = f"src:{PLAZA_MAYOR}:{city}"
            if force or not await public_service.is_fresh(session, key):
                end = today + timedelta(days=HORIZON_DAYS)
                url = ("https://plazamayor.com.co/wp-json/tribe/events/v1/events"
                       f"?start_date={today.isoformat()}&end_date={end.isoformat()}&per_page=50")
                try:
                    body = await fetcher.get(url, ALLOWED_HOSTS[PLAZA_MAYOR])
                    evs = plaza_mayor_events(json.loads(body)) if body else []
                except (PermissionError, json.JSONDecodeError) as exc:
                    report.errors.append(f"{PLAZA_MAYOR}: {type(exc).__name__}")
                    evs = []
                for ev in evs:
                    await _save(session, ev, city, report, today)
                report.sources[f"{PLAZA_MAYOR}:{city}"] = len(evs)
                await public_service.mark_scanned(session, key, len(evs))
    finally:
        await fetcher.aclose()
    await session.flush()
    return report


async def refresh_holidays(session: AsyncSession, today: date | None = None) -> int:
    """Puentes festivos y Semana Santa del próximo año, con clave nacional (todas las ciudades)."""
    today = today or date.today()
    n = 0
    for w in holidays_co.long_weekends(today, today + timedelta(days=HORIZON_DAYS)):
        await event_service.upsert_event(
            session, name=w.name, start_date=w.first_night,
            end_date=w.last_night if w.last_night != w.first_night else None,
            kind=EventKind.holiday, relevance=Relevance.high if w.high else Relevance.medium,
            city=municipalities.NATIONAL,
        )
        n += 1
    return n


# --------- búsquedas dirigidas (Tavily) ---------

TICKET_DOMAINS = ["tuboleta.com", "ticketmaster.co"]
_MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre", "octubre", "noviembre", "diciembre"]
TARGETED = "targeted_search"


def targeted_queries(city: str, today: date) -> list[tuple[str, dict]]:
    """Por mes en las boleteras (los artículos de "agenda" no traen conciertos privados) y una
    de noticias de la semana para anuncios nuevos."""
    out: list[tuple[str, dict]] = []
    for i in range(3):
        y, m = divmod(today.month - 1 + i, 12)
        out.append((f"conciertos y eventos {city} {_MONTHS[m]} {today.year + y}",
                    {"include_domains": TICKET_DOMAINS, "search_depth": "advanced"}))
    out.append((f"anuncian concierto en {city}", {"topic": "news", "time_range": "week"}))
    return out


async def targeted_search(session: AsyncSession, city: str, core_key: str, search, llm,
                          today: date | None = None) -> int:
    """Una vez por semana por ciudad principal (`city_scan` "tav:<ciudad>")."""
    from app.market.extractor import extract_events
    from app.services import public_service

    today = today or date.today()
    key = f"tav:{core_key}"
    if search is None or llm is None or await public_service.is_fresh(session, key):
        return 0
    found = 0
    for query, opts in targeted_queries(city, today):
        try:
            results = await search.search(query, max_results=20, **opts)
        except TypeError:  # proveedor sin opciones avanzadas
            results = await search.search(query, max_results=10)
        await public_service.bump(session, TARGETED)
        for cand in await extract_events(llm, results, city, today):
            await event_service.upsert_event(
                session, name=cand.name, start_date=cand.start_date, kind=cand.kind,
                end_date=cand.end_date, relevance=cand.relevance, location=cand.location,
                city=core_key,
            )
            found += 1
    await public_service.mark_scanned(session, key, found)
    return found


async def refresh_area(session: AsyncSession, city_text: str, *, search=None, llm=None,
                       today: date | None = None) -> str:
    """Escaneo diario (cron): fuentes estructuradas + búsquedas dirigidas de la ciudad principal
    del área de una propiedad. Cada parte se hace como mucho una vez por semana."""
    today = today or date.today()
    core_key = municipalities.area_core_key(city_text)
    core = municipalities.by_city_key(core_key)
    notes = []
    rep = await refresh_city(session, core_key, today=today)
    if rep.sources:
        notes.append(f"fuentes {rep.sources} guardados={rep.saved} cancelados={rep.cancelled}")
    if rep.errors:
        notes.append(f"bloqueos={rep.errors}")
    n = await targeted_search(session, core.city if core else city_text, core_key, search, llm,
                              today)
    if n:
        notes.append(f"búsquedas dirigidas={n}")
    return "; ".join(notes)


async def refresh_holidays_weekly(session: AsyncSession, today: date | None = None) -> int:
    from app.services import public_service

    key = f"src:{HOLIDAYS}"
    if await public_service.is_fresh(session, key):
        return 0
    n = await refresh_holidays(session, today)
    await public_service.mark_scanned(session, key, n)
    return n
