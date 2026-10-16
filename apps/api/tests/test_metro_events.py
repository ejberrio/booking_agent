"""Feature 033: las sugerencias usan los eventos de la ciudad principal del área metropolitana."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.domain import municipalities
from app.models.public import CityScan
from app.services import event_service, public_service
from scripts import scan_daily
from tests.test_suggestion_engine import E1, E3, _event, _generate, _seed

pytestmark = pytest.mark.anyio


def test_claves_del_area():
    assert municipalities.area_keys("Sabaneta") == ["sabaneta", "medellin"]
    assert municipalities.area_keys("Envigado, Antioquia") == ["envigado", "medellin"]
    assert municipalities.area_keys("Medellín") == ["medellin"]
    assert municipalities.area_keys("Guatapé") == ["guatape"]
    assert municipalities.area_keys("Ciudad inventada") == ["ciudad inventada"]
    assert municipalities.area_keys("Soacha") == ["soacha", "bogota"]


async def test_sabaneta_recibe_eventos_de_medellin_sin_duplicados(session):
    prop, unit = await _seed(session)  # propiedad en Sabaneta
    medellin = _event(name="Beéle — Borondo Tour")
    medellin.city = "medellin"
    sabaneta = _event(name="Beele - Borondo tour")  # el mismo, visto en Sabaneta
    session.add_all([medellin, sabaneta])
    await session.flush()
    sugs = [s for s in await _generate(session, unit) if s.date_from == E1]
    assert len(sugs) == 1 and sugs[0].date_to == E3
    assert len(event_service.unique_events([medellin, sabaneta])) == 1


async def test_guatape_no_recibe_los_de_medellin(session):
    prop, unit = await _seed(session)
    prop.city = "Guatapé"
    ev = _event()
    ev.city = "medellin"
    session.add(ev)
    await session.flush()
    sugs = await _generate(session, unit)
    kinds = {f["kind"] for s in sugs for f in (s.rationale or {}).get("factors", [])}
    assert "event" not in kinds  # puede haber descuentos por hueco, pero no por el evento


async def test_escaneo_busca_la_ciudad_principal_solo_si_no_esta_fresca(session, monkeypatch):
    calls: list[str] = []

    async def fake_search_city(s, m, search, llm):
        calls.append(m.city_key)
        return 3

    monkeypatch.setattr(public_service, "search_city", fake_search_city)
    scanned: set[str] = set()
    note = await scan_daily._refresh_area(session, "Sabaneta", scanned, object(), object())
    assert calls == ["medellin"] and "medellin" in note
    assert (await session.get(CityScan, "medellin")).events_found == 3
    # fresca (< 7 días): no se busca otra vez, ni en otra cuenta de la misma corrida
    await scan_daily._refresh_area(session, "Envigado", set(), object(), object())
    assert calls == ["medellin"]
    # vieja: se vuelve a buscar
    row = await session.get(CityScan, "medellin")
    row.scanned_at = row.scanned_at - timedelta(days=8)
    await scan_daily._refresh_area(session, "Envigado", set(), object(), object())
    assert calls == ["medellin", "medellin"]
    # sin búsqueda configurada no hace nada
    assert await scan_daily._refresh_area(session, "Bello", set(), None, None) == ""
