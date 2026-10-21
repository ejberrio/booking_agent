"""Feature 040: cargar el CSV de PriceLabs ("Precios Futuros") desde Administración."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.db.session import get_session
from app.db.tenancy import mark_platform
from app.email.fake import FakeEmailSender
from app.main import app
from app.models.market import MarketBand
from app.services import admin_service, auth_service
from app.services import market_band_service as svc

pytestmark = pytest.mark.anyio

PWD = "una-clave-larga-1"
TODAY = date.today()
HEAD = "Dates,25th Percentile,50th Percentile,75th Percentile,90th Percentile,Median Booked Price,No. Of Bookings"


def _csv(days=range(-3, 5), head=HEAD, sep=","):
    lines = [head.replace(",", sep)]
    for i in days:
        d = (TODAY + timedelta(days=i)).isoformat()
        lines.append(sep.join([d, "157883.4", "216300.0", "275506.2", f"{322082 + i}.7", "171735.0", "12.0"]))
    return "﻿" + "\n".join(lines) + "\n"


def test_lee_el_csv_de_pricelabs_y_omite_el_historial():
    p = svc.parse_csv(_csv())
    assert p.past == 3 and p.invalid == 0 and len(p.rows) == 5
    assert p.rows[0] == [TODAY.isoformat(), 157883.4, 216300.0, 275506.2, 322082.7]


def test_columnas_en_otro_orden_en_espanol_y_con_punto_y_coma():
    head = "Fecha;Precio Medio Reservado;Percentil 90;Percentil 75;Percentil 50;Percentil 25"
    text = f"{head}\n{TODAY.isoformat()};171735;322082;275506;216300;157883\n"
    p = svc.parse_csv(text)
    assert p.rows == [[TODAY.isoformat(), 157883.0, 216300.0, 275506.0, 322082.0]]


def test_filas_raras_se_cuentan_y_archivo_equivocado_se_rechaza():
    bad = (f"{HEAD}\n{TODAY.isoformat()},300,200,100,50,1,1\n"
           f"no-es-fecha,1,2,3,4,5,6\n{TODAY.isoformat()},,2,3,4,5,6\n"
           f"{(TODAY + timedelta(days=1)).isoformat()},1,2,3,4,5,6\n")
    p = svc.parse_csv(bad)
    assert p.invalid == 3 and len(p.rows) == 1
    with pytest.raises(svc.CsvError, match="Precios Futuros"):
        svc.parse_csv("Dates,Occupancy\n2026-10-20,49\n")
    with pytest.raises(svc.CsvError):
        svc.parse_csv(_csv(days=range(-5, 0)))  # solo historial


@pytest.fixture
def mail(monkeypatch):
    sender = FakeEmailSender()
    monkeypatch.setattr(auth_service, "get_email_sender", lambda: sender)
    return sender


@pytest_asyncio.fixture
async def client(session, monkeypatch):
    maker = session.info["maker"]

    async def _fresh():
        async with maker() as s:
            yield s

    @asynccontextmanager
    async def fake_platform():
        async with maker() as s:
            mark_platform(s)
            yield s

    monkeypatch.setattr(admin_service, "platform_session", fake_platform)
    app.dependency_overrides[get_session] = _fresh
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def _admin(client) -> dict:
    r = await client.post("/auth/claim", json={"name": "Host", "email": "host@example.com",
                                               "password": PWD, "accept_terms": True})
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def test_carga_desde_administracion_reemplaza_y_se_puede_borrar(client, session):
    h = await _admin(client)
    r = await client.post("/admin/market-bands/csv", headers=h,
                          json={"city": "Sabaneta", "bedrooms": 3, "csv": _csv()})
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["imported"], body["past"], body["city"]) == (5, 3, "medellin")
    band = body["bands"][0]
    assert (band["city"], band["bedrooms"], band["days"], band["p50_avg"]) == ("medellin", 3, 5, 216300)
    assert band["updated_at"]

    # una segunda carga reemplaza las fechas (sin duplicar) y agrega las nuevas
    await client.post("/admin/market-bands/csv", headers=h,
                      json={"city": "Medellín", "bedrooms": 3, "csv": _csv(days=range(0, 8))})
    rows = (await session.execute(select(MarketBand))).scalars().all()
    assert len(rows) == 8
    assert {r.p90 for r in rows if r.day == TODAY} == {Decimal("322083")}
    caps = await svc.caps_for(session, "Envigado", 3, TODAY, TODAY + timedelta(days=7))
    assert len(caps) == 8  # todo el área usa la zona de Medellín

    r = await client.delete("/admin/market-bands", headers=h, params={"city": "Medellín", "bedrooms": 3})
    assert r.json()["deleted"] == 8 and r.json()["bands"] == []


async def test_validaciones_y_solo_el_administrador(client, mail):
    h = await _admin(client)
    r = await client.post("/admin/market-bands/csv", headers=h,
                          json={"city": "Ciudad Gótica", "bedrooms": 3, "csv": _csv()})
    assert r.status_code == 400 and "municipio" in r.json()["detail"]
    r = await client.post("/admin/market-bands/csv", headers=h,
                          json={"city": "Medellín", "bedrooms": 3, "csv": "Dates,Occupancy\n2026-10-20,49\n"})
    assert r.status_code == 400 and "Precios Futuros" in r.json()["detail"]
    # otro anfitrión (no administrador de plataforma) no puede cargar datos de mercado
    await client.patch("/admin/beta", headers=h, json={"enabled": True})
    await client.post("/auth/register", json={
        "name": "Ana", "email": "ana@example.com", "password": PWD, "accept_terms": True})
    link = re.search(r"token=([A-Za-z0-9_\-]+)", mail.sent[-1].text).group(1)
    tok = (await client.post("/auth/verify-email", json={"token": link})).json()["token"]
    r = await client.post("/admin/market-bands/csv", headers={"Authorization": f"Bearer {tok}"},
                          json={"city": "Medellín", "bedrooms": 3, "csv": _csv()})
    assert r.status_code == 403


async def test_un_anio_se_carga_con_una_sola_consulta(session):
    from sqlalchemy import event

    rows = [[(TODAY + timedelta(days=i)).isoformat(), 160000, 220000, 290000, 350000 + i]
            for i in range(365)]
    await svc.import_rows(session, city="Medellín", bedrooms=3, rows=rows[:100])
    selects: list[str] = []
    engine = session.bind.sync_engine

    def count(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "market_band" in statement:
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        n = await svc.import_rows(session, city="Medellín", bedrooms=3, rows=rows)
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert n == 365 and len(selects) == 1
    bands = (await session.execute(select(MarketBand))).scalars().all()
    assert len(bands) == 365  # las 100 que ya existían se reemplazan, no se duplican
    assert {b.p90 for b in bands if b.day == TODAY} == {Decimal("350000")}
