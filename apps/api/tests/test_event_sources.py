"""Feature 034: fuentes estructuradas de eventos, festivos y área metropolitana en ambos sentidos."""

from __future__ import annotations

import json
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.domain import holidays_co
from app.models.enums import EventKind, Relevance
from app.models.market import Event
from app.services import event_service, event_sources_service as src

pytestmark = pytest.mark.anyio

TODAY = date(2026, 10, 16)


def _ld(**ev) -> str:
    return f'<html><script type="application/ld+json">{json.dumps(ev)}</script></html>'


HV = _ld(**{
    "@context": "https://schema.org", "@type": "MusicEvent",
    "name": "Hebert Vargas · Éxito tras Éxito", "startDate": "2026-12-04T20:00:00-05:00",
    "eventStatus": "https://schema.org/EventScheduled",
    "url": "https://tuboleta.com/es/eventos/hebert-vargas-exito-tras-exito-medellin",
    "location": {"@type": "Place", "name": "DAVIarena",
                 "address": {"addressLocality": "Sabaneta", "addressRegion": "Antioquia"}},
})
JUANES = _ld(**{
    "@type": "MusicEvent", "name": "Juanes · World Tour 2026",
    "startDate": "2026-11-14T20:00:00-05:00",
    "location": {"name": "DAVIarena", "address": {"addressLocality": "Sabaneta"}},
})
CANCELADO = _ld(**{
    "@type": "MusicEvent", "name": "Concierto cancelado", "startDate": "2026-11-20T20:00:00-05:00",
    "eventStatus": "https://schema.org/EventCancelled",
    "location": {"name": "Teatro Metropolitano", "address": {"addressLocality": "Medellín"}},
})


def test_festivos_y_puentes_coinciden_con_nager():
    n26 = ["01-01", "01-12", "03-23", "04-02", "04-03", "05-01", "05-18", "06-08", "06-15",
           "06-29", "07-13", "07-20", "08-07", "08-17", "10-12", "11-02", "11-16", "12-08", "12-25"]
    assert [d.strftime("%m-%d") for d in holidays_co.holidays(2026)] == n26
    assert len(holidays_co.holidays(2027)) == 19 and date(2027, 3, 26) in holidays_co.holidays(2027)
    weeks = holidays_co.long_weekends(TODAY, date(2026, 12, 31))
    nov = next(w for w in weeks if "Todos los Santos" in w.name)
    assert (nov.first_night, nov.last_night) == (date(2026, 10, 30), date(2026, 11, 1))
    assert next(w for w in weeks if "Navidad" in w.name).high


def test_jsonld_tuboleta_ticketmaster_y_plaza_mayor():
    ev = src.events_from_jsonld(HV, "https://tuboleta.com/x")[0]
    assert (ev.name, ev.start, ev.venue, ev.locality) == (
        "Hebert Vargas · Éxito tras Éxito", date(2026, 12, 4), "DAVIarena", "Sabaneta")
    assert ev.kind is EventKind.concert and src.relevance_for(ev) is Relevance.high
    assert src.city_key_for(ev, "medellin") == "sabaneta"
    # Ticketmaster da la hora en UTC: 2027-04-12T00:00Z es el 11 de abril en Colombia
    tm = _ld(**{"@type": "Event", "name": "Caifanes | Medellin",
                "startDate": "2027-04-12T00:00:00Z", "endDate": "2027-04-12T03:00:00Z",
                "location": {"name": "City Hall El Rodeo",
                             "address": {"addressLocality": "Medellín"}}})
    t = src.events_from_jsonld(tm, "u")[0]
    assert t.start == date(2027, 4, 11) and src.relevance_for(t) is Relevance.medium
    assert src.events_from_jsonld(CANCELADO, "u")[0].cancelled
    pm = src.plaza_mayor_events({"events": [
        {"title": "Comic Con 2026", "start_date": "2026-11-27 10:00:00",
         "end_date": "2026-11-29 20:00:00", "url": "https://plazamayor.com.co/event/comic-con-2026/"},
        {"title": "Comic Con 2026", "start_date": "2026-11-27 10:00:00",
         "end_date": "2026-11-29 20:00:00", "url": "https://plazamayor.com.co/en/event/comic-con-2026/"},
    ]})
    assert len(pm) == 1 and pm[0].kind is EventKind.fair and pm[0].end == date(2026, 11, 29)
    links = src.tuboleta_links('<a href="/es/eventos/a-b"></a><a href="https://tuboleta.com/es/eventos/a-b"></a>')
    assert links == ["https://tuboleta.com/es/eventos/a-b"]


def _transport(pages: dict[str, tuple[int, str]], calls: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        calls.append(url)
        if url.endswith("/robots.txt"):
            body = "User-agent: *\nDisallow: /search/\n" if "tuboleta" in url else ""
            return httpx.Response(200, text=body)
        for key, (status, body) in pages.items():
            if key in url:
                return httpx.Response(status, text=body)
        return httpx.Response(404, text="")
    return httpx.MockTransport(handler)


async def test_lee_tuboleta_guarda_cancela_y_respeta_semana(session, monkeypatch):
    monkeypatch.setattr(settings, "event_sources_disabled", "ticketmaster,plazamayor")
    listing = ('<a href="/es/eventos/hebert-vargas-exito-tras-exito-medellin"></a>'
               '<a href="/es/eventos/juanes-world-tour-2026-medellin"></a>'
               '<a href="/es/eventos/concierto-cancelado"></a>')
    calls: list[str] = []
    pages = {"page=0": (200, listing), "page=1": (200, listing),
             "hebert-vargas": (200, HV), "juanes-world": (200, JUANES),
             "concierto-cancelado": (200, CANCELADO)}
    # un evento que luego aparece cancelado en la boletera
    await event_service.upsert_structured(
        session, name="Concierto cancelado", start_date=date(2026, 11, 20), end_date=None,
        kind=EventKind.concert, relevance=Relevance.low, location=None,
        source_url="https://tuboleta.com/es/eventos/concierto-cancelado", city="medellin",
        area=["medellin"])
    # y lo que la búsqueda con IA ya había encontrado con otro nombre
    await event_service.upsert_event(session, name="Concierto de Hebert Vargas",
                                     start_date=date(2026, 12, 4), kind=EventKind.concert,
                                     relevance=Relevance.medium, city="Medellín")
    await session.flush()
    for e in (await session.execute(select(Event))).scalars():  # leídos hace más de una semana
        e.updated_at = e.updated_at - timedelta(days=8)
    rep = await src.refresh_city(session, "medellin", today=TODAY,
                                 transport=_transport(pages, calls), delay=0)
    assert rep.saved == 2 and rep.cancelled == 1 and not rep.errors
    assert not any("page=2" in c for c in calls)  # la página 2 repitió enlaces: se detiene
    evs = {e.name: e for e in (await session.execute(select(Event))).scalars()}
    hv = evs["Hebert Vargas · Éxito tras Éxito"]  # se fusionó con el de la IA (mismo día)
    assert "Concierto de Hebert Vargas" not in evs and "Concierto cancelado" not in evs
    assert (hv.city, hv.relevance, hv.location) == ("sabaneta", Relevance.high, "DAVIarena")
    assert hv.source_url.endswith("hebert-vargas-exito-tras-exito-medellin")
    # misma semana: no vuelve a leer
    calls.clear()
    await src.refresh_city(session, "medellin", today=TODAY, transport=_transport(pages, calls),
                           delay=0)
    assert calls == []


async def test_bloqueo_robots_y_apagado(session, monkeypatch):
    monkeypatch.setattr(settings, "event_sources_disabled", "ticketmaster,plazamayor")
    calls: list[str] = []
    blocked = {"page=0": (403, "Forbidden")}
    rep = await src.refresh_city(session, "medellin", today=TODAY,
                                 transport=_transport(blocked, calls), delay=0)
    assert rep.errors and rep.saved == 0  # se registra y no se insiste
    monkeypatch.setattr(settings, "event_sources_disabled", "all")
    rep = await src.refresh_city(session, "bogota", today=TODAY, force=True,
                                 transport=_transport({}, calls := []), delay=0)
    assert rep.skipped == ["all"] and calls == []

    def robots_no(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        raise AssertionError("no debe pedir páginas prohibidas por robots.txt")
    f = src.Fetcher(httpx.MockTransport(robots_no), delay=0)
    assert await f.get("https://tuboleta.com/es/eventos/x", ("tuboleta.com",)) is None
    assert await f.get("https://evil.com/x", ("tuboleta.com",)) is None
    await f.aclose()


async def test_medellin_ve_eventos_de_sabaneta_y_festivos(session):
    from tests.test_suggestion_engine import _generate, _seed

    prop, unit = await _seed(session)
    prop.city = "Medellín"
    start = date(2026, 9, 10)
    await event_service.upsert_event(session, name="Concierto DAVIarena", start_date=start,
                                     kind=EventKind.concert, relevance=Relevance.high,
                                     city="Sabaneta")
    assert await src.refresh_holidays(session, date(2026, 9, 1)) > 0  # octubre en adelante
    await event_service.upsert_event(session, name="Puente festivo: prueba",
                                     start_date=date(2026, 9, 19), kind=EventKind.holiday,
                                     relevance=Relevance.medium, city="colombia")
    await session.flush()
    sugs = await _generate(session, unit)
    names = {(f.get("event") or {}).get("name") for s in sugs
             for f in (s.rationale or {}).get("factors", [])}
    assert "Concierto DAVIarena" in names
    assert any(x and x.startswith("Puente festivo") for x in names)


class OptsSearch:
    def __init__(self):
        self.calls = []

    async def search(self, query, *, max_results=5, **opts):
        self.calls.append((query, max_results, opts))
        return []


async def test_busquedas_dirigidas_semanales(session):
    q = src.targeted_queries("Medellín", TODAY)
    assert q[0][0] == "conciertos y eventos Medellín octubre 2026"
    assert q[2][0].endswith("diciembre 2026") and q[0][1]["include_domains"] == src.TICKET_DOMAINS
    s = OptsSearch()
    await src.targeted_search(session, "Medellín", "medellin", s, object(), TODAY)
    assert len(s.calls) == 4 and s.calls[0][1] == 20 and s.calls[3][2]["topic"] == "news"
    await src.targeted_search(session, "Medellín", "medellin", s, object(), TODAY + timedelta(days=2))
    assert len(s.calls) == 4  # semanal
