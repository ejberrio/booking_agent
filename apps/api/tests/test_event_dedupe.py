"""Feature 036: limpieza de eventos repetidos y con fecha equivocada en el área."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.domain import municipalities
from app.models.enums import EventKind, Relevance
from app.models.market import Event
from app.services import event_service

pytestmark = pytest.mark.anyio

TODAY = date(2026, 10, 19)
D5 = date(2026, 12, 5)


def _ev(name, day, city, rel=Relevance.medium, url=None, loc=None, kind=EventKind.concert):
    return Event(name=name, start_date=day, kind=kind, relevance=rel, city=city, location=loc,
                 source_url=url, dedup_key=f"{name}|{day}|{city}")


async def test_limpieza_fusiona_repetidos_y_borra_fecha_equivocada(session):
    session.add_all([
        _ev("Martin Garrix", D5, "medellin", Relevance.high),
        _ev("Martin Garrix Show", D5, "medellin"),
        _ev("Martin Garrix Concert", D5, "medellin", loc="Estadio"),
        _ev("Martin Garrix", date(2026, 12, 1), "medellin", Relevance.high),  # fecha equivocada
        _ev("Martin Garrix · Americas Tour", D5, "sabaneta", Relevance.high,
            url="https://tuboleta.com/es/eventos/martin-garrix", loc="DAVIarena"),
        _ev("Hebert Vargas · Éxito tras Éxito", date(2026, 12, 4), "medellin", Relevance.high),
        _ev("Hebert Vargas · Éxito tras Éxito", date(2026, 12, 4), "sabaneta", Relevance.high,
            url="https://tuboleta.com/es/eventos/hebert", loc="DAVIarena"),
        _ev("Ballet Cascanueces", date(2026, 12, 4), "medellin", Relevance.low),  # otro evento
        _ev("Puente festivo: Inmaculada", date(2026, 12, 7), "colombia",
            kind=EventKind.holiday),
        _ev("Concierto en Guatapé", D5, "guatape"),  # otra área: no se toca
    ])
    await session.flush()
    res = await event_service.dedupe_area(session, municipalities.area_keys("Medellín"), TODAY)
    assert res == {"merged": 4, "wrong_date": 1}
    left = sorted((e.start_date.isoformat(), e.name, e.city)
                  for e in (await session.execute(select(Event))).scalars())
    assert left == [
        ("2026-12-04", "Ballet Cascanueces", "medellin"),
        ("2026-12-04", "Hebert Vargas · Éxito tras Éxito", "sabaneta"),
        ("2026-12-05", "Concierto en Guatapé", "guatape"),
        ("2026-12-05", "Martin Garrix · Americas Tour", "sabaneta"),
        ("2026-12-07", "Puente festivo: Inmaculada", "colombia"),
    ]
    # idempotente
    assert await event_service.dedupe_area(
        session, municipalities.area_keys("Medellín"), TODAY) == {"merged": 0, "wrong_date": 0}


async def test_nuevo_evento_de_busqueda_no_se_duplica_en_el_area(session):
    session.add(_ev("Hebert Vargas · Éxito tras Éxito", date(2026, 12, 4), "sabaneta",
                    Relevance.high, url="https://tuboleta.com/x", loc="DAVIarena"))
    await session.flush()
    ev = await event_service.upsert_event(session, name="Concierto de Hebert Vargas",
                                          start_date=date(2026, 12, 4), kind=EventKind.concert,
                                          relevance=Relevance.medium, city="Medellín")
    assert ev.city == "sabaneta"  # devolvió el de la boletera
    assert len((await session.execute(select(Event))).scalars().all()) == 1
    best = event_service.unique_events([
        _ev("Hebert Vargas", date(2026, 12, 4), "medellin"),
        _ev("Hebert Vargas · Éxito tras Éxito", date(2026, 12, 4), "sabaneta", url="https://t/x"),
    ])
    assert len(best) == 1 and best[0].source_url == "https://t/x"


async def test_grupos_transitivos_y_ballet_con_varias_funciones(session):
    d14 = date(2026, 11, 14)
    session.add_all([
        _ev("Juanes · World Tour 2026", d14, "sabaneta", Relevance.high, url="https://t/j"),
        _ev("Concierto de Juanes", d14, "medellin"),
        _ev("JUANES", d14, "medellin"),
        _ev("Concierto inaugural de Juanes en DAVIarena", d14, "medellin"),
        _ev("La Fille Mal Gardée", date(2026, 11, 15), "medellin", Relevance.low,
            url="https://ticketmaster.co/event/x", kind=EventKind.other),
        _ev("La Fille Mal Gardée", date(2026, 11, 11), "medellin", kind=EventKind.other),
    ])
    await session.flush()
    res = await event_service.dedupe_area(session, municipalities.area_keys("Sabaneta"), TODAY)
    assert res == {"merged": 3, "wrong_date": 0}
    names = sorted(e.name for e in (await session.execute(select(Event))).scalars())
    assert names == ["Juanes · World Tour 2026", "La Fille Mal Gardée", "La Fille Mal Gardée"]
