"""Feature 023: extender precios hacia el futuro (vista previa, aplicación por mes, aviso, precio 0)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.api.routes import pricing as pricing_routes
from app.channels.base import (
    CalendarEntry,
    ConnectionInfo,
    RemoteProperty,
    RemoteRate,
    RemoteRoom,
    WriteResult,
)
from app.channels.beds24_v2 import Beds24V2Adapter
from app.db.session import get_session
from app.main import app
from app.models.audit import PriceChangeLog
from app.models.availability import AvailabilityChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay, Rate
from app.models.enums import BookingStatus, ChangeOrigin, ChannelKind
from app.models.pricing import PricingRule
from app.models.property import Channel, Property, UnitType
from app.models.sync import SyncIssue
from app.services import pricing_app_service, pricing_service, suggestion_engine, sync_service
from app.services import price_extension_service as ext
from app.services.price_extension_service import ExtensionError, ExtensionParams, MonthInput

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date(2036, 10, 8)  # "hoy" inyectado (miércoles)
PRICED = 30  # noches 0..29 con precio en el CM


def day(n: int) -> date:
    return TODAY + timedelta(days=n)


class FakeCM:
    """CM falso: calendario remoto en memoria (precio, disponibilidad)."""

    def __init__(self, *, priced_days=PRICED, horizon=800, fail_months=(), ignore_avail=False):
        self.ignore_avail = ignore_avail
        self.cal: dict[date, tuple[Decimal, int]] = {}
        for i in range(horizon):
            self.cal[day(i)] = (D("300000"), 1) if i < priced_days else (D("0"), 0)
        self.fail_months = set(fail_months)
        self.writes: list[list[CalendarEntry]] = []

    async def get_rates(self, room, df, dt):
        out, d = [], df
        while d <= dt:
            p, a = self.cal.get(d, (D("0"), 0))
            out.append(RemoteRate(room, d, p, a))
            d += timedelta(days=1)
        return out

    async def set_calendar_entries(self, room, entries):
        self.writes.append(entries)
        if any(f"{e.date_from:%Y-%m}" in self.fail_months for e in entries):
            return WriteResult(ok=True, verified=False, detail="no verificado")
        for e in entries:
            d = e.date_from
            while d <= e.date_to:
                _, a = self.cal.get(d, (D("0"), 0))
                keep = self.ignore_avail or e.num_avail is None
                self.cal[d] = (e.price, a if keep else e.num_avail)
                d += timedelta(days=1)
        if self.ignore_avail and any(e.num_avail is not None for e in entries):
            # como Beds24 en producción: guarda el precio, no la apertura
            n = sum((e.date_to - e.date_from).days + 1 for e in entries if e.num_avail is not None)
            return WriteResult(ok=True, verified=True, detail="precio confirmado; la apertura no se confirmó", unconfirmed=n)
        return WriteResult(ok=True, verified=True)

    async def aclose(self):
        return None


async def _seed(session, *, min_price=None):
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411", units_count=1)
    session.add(unit)
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    await session.flush()
    for i in range(PRICED):
        session.add(Rate(unit_type_id=unit.id, date=day(i), base_price=D("300000")))
    if min_price:
        session.add(PricingRule(property_id=prop.id, min_price=D(min_price), is_active=True))
    await session.flush()
    return prop, unit


async def _count(session, model, *where) -> int:
    q = select(func.count()).select_from(model)
    for w in where:
        q = q.where(w)
    return int((await session.execute(q)).scalar_one())


async def test_clasificacion_y_aplicacion(session):
    prop, unit = await _seed(session)
    cm = FakeCM()
    cm.cal[day(30)] = (D("0"), 1)  # abierta sin precio (como el 1–3 may)
    session.add(Booking(unit_type_id=unit.id, channel_kind=ChannelKind.booking, check_in=day(40),
                        check_out=day(42), status=BookingStatus.confirmed))
    session.add(CalendarDay(unit_type_id=unit.id, date=day(50), units_available=0, is_blocked=True))
    await session.flush()
    params = ExtensionParams(unit_type_id=unit.id, until=day(60))
    p = await ext.preview(session, cm, params, today=TODAY)
    assert p.first_target == day(30)
    assert p.total_nights == 31 - 2  # 30..60 sin las 2 reservadas
    assert sum(m.kept_closed for m in p.months) == 1  # bloqueada por el host
    assert p.total_to_open == 29 - 1 - 1  # sin la ya abierta (30) ni la bloqueada (50)
    assert all(m.proposed_price == D("300000") for m in p.months)

    r = await ext.apply(session, cm, params, p.fingerprint, today=TODAY)
    assert r.failed_months == 0 and r.applied_nights == 29 and r.opened_nights == 27
    assert len(cm.writes) == len([m for m in p.months if m.nights])  # una escritura por mes
    # noches con precio previo intactas; reservadas sin tocar; bloqueada con precio pero cerrada
    assert await _count(session, PriceChangeLog, PriceChangeLog.date < day(30)) == 0
    assert cm.cal[day(5)] == (D("300000"), 1)
    assert cm.cal[day(40)] == (D("0"), 0)
    assert cm.cal[day(50)] == (D("300000"), 0)
    assert cm.cal[day(33)] == (D("300000"), 1)
    assert await pricing_service.get_price(session, unit.id, day(50)) == D("300000")
    logs = (await session.execute(select(PriceChangeLog))).scalars().all()
    assert len(logs) == 29 and {log.origin for log in logs} == {ChangeOrigin.extension}
    assert await _count(session, AvailabilityChangeLog, AvailabilityChangeLog.origin == ChangeOrigin.extension) == 27
    cd50 = (await session.execute(select(CalendarDay).where(CalendarDay.date == day(50)))).scalar_one()
    assert cd50.is_blocked is True

    # una segunda vista previa ya no encuentra noches por extender
    p2 = await ext.preview(session, cm, params, today=TODAY)
    assert p2.total_nights == 0 and p2.first_target is None


async def test_plantilla_editable_exclusion_fin_de_semana_y_minimo(session):
    prop, unit = await _seed(session, min_price="230000")
    cm = FakeCM()
    params = ExtensionParams(unit_type_id=unit.id, until=day(90), weekend_pct=D("10"))
    p = await ext.preview(session, cm, params, today=TODAY)
    keys = [m.month for m in p.months]
    assert keys == ["2036-11", "2036-12", "2037-01"]
    nov = p.months[0]
    assert nov.weekday_price == D("300000") and nov.weekend_price == D("330000")

    params.months = [MonthInput("2036-11", D("200000")), MonthInput("2036-12", None, included=False)]
    p = await ext.preview(session, cm, params, today=TODAY)
    nov, dec = p.months[0], p.months[1]
    # 200.000 entre semana → ajustado al mínimo; fin de semana 220.000 → también
    assert nov.price == D("200000") and nov.weekday_price == D("230000") and nov.clipped_min == nov.nights
    assert dec.included is False and p.total_nights == nov.nights + p.months[2].nights
    r = await ext.apply(session, cm, params, p.fingerprint, today=TODAY)
    assert [m.status for m in r.months] == ["applied", "skipped", "applied"]
    assert cm.cal[date(2036, 12, 15)] == (D("0"), 0)
    assert await pricing_service.get_price(session, unit.id, date(2036, 11, 11)) == D("230000")


async def test_validaciones(session):
    prop, unit = await _seed(session)
    cm = FakeCM()
    with pytest.raises(ExtensionError):
        await ext.preview(session, cm, ExtensionParams(unit.id, until=day(800)), today=TODAY)
    with pytest.raises(ExtensionError):
        await ext.preview(session, cm, ExtensionParams(unit.id, weekend_pct=D("60")), today=TODAY)
    with pytest.raises(ExtensionError):
        await ext.preview(
            session, cm, ExtensionParams(unit.id, months=[MonthInput("2036-11", D("0"))]), today=TODAY
        )


async def test_obsoleta_no_escribe(session):
    prop, unit = await _seed(session)
    cm = FakeCM()
    params = ExtensionParams(unit_type_id=unit.id, until=day(60))
    p = await ext.preview(session, cm, params, today=TODAY)
    cm.cal[day(45)] = (D("350000"), 1)  # alguien cargó precio en Beds24 entretanto
    r = await ext.apply(session, cm, params, p.fingerprint, today=TODAY)
    assert r.stale and cm.writes == []
    assert await _count(session, PriceChangeLog) == 0


async def test_fallo_de_un_mes_se_deshace_y_los_demas_siguen(session):
    prop, unit = await _seed(session)
    cm = FakeCM(fail_months={"2036-12"})
    params = ExtensionParams(unit_type_id=unit.id, until=day(90))
    p = await ext.preview(session, cm, params, today=TODAY)
    r = await ext.apply(session, cm, params, p.fingerprint, today=TODAY)
    assert [(m.month, m.status) for m in r.months] == [
        ("2036-11", "applied"), ("2036-12", "failed"), ("2037-01", "applied")
    ]
    assert r.failed_months == 1
    assert await pricing_service.get_price(session, unit.id, date(2036, 12, 10)) is None
    assert await _count(session, AvailabilityChangeLog, AvailabilityChangeLog.date == date(2036, 12, 10)) == 0
    assert await pricing_service.get_price(session, unit.id, date(2037, 1, 2)) == D("300000")
    issues = (await session.execute(select(SyncIssue))).scalars().all()
    assert [i.entity_ref for i in issues] == ["price-extension:2036-12"]


async def test_apertura_no_confirmada_es_aviso_y_cada_mes_se_guarda(session):
    prop, unit = await _seed(session)
    cm = FakeCM(ignore_avail=True)
    params = ExtensionParams(unit_type_id=unit.id, until=day(90))
    p = await ext.preview(session, cm, params, today=TODAY)
    commits: list[int] = []

    async def done():
        commits.append(await _count(session, PriceChangeLog))

    r = await ext.apply(session, cm, params, p.fingerprint, today=TODAY, on_month_done=done)
    assert [m.status for m in r.months] == ["applied"] * 3 and r.failed_months == 0
    assert all(m.detail and "apertura" in m.detail for m in r.months)
    # el callback corre tras CADA mes, con lo de ese mes ya escrito
    assert len(commits) == 3 and commits[0] < commits[1] < commits[2]
    issues = (await session.execute(select(SyncIssue))).scalars().all()
    assert len(issues) == 3 and all(i.kind.value == "write_unverified" for i in issues)
    assert await pricing_service.get_price(session, unit.id, day(40)) == D("300000")
    # la app refleja lo que quedó de verdad: cerradas, y se informa cuántas
    assert r.opened_nights == 0 and r.not_opened_nights == p.total_to_open > 0
    assert all(m.not_opened == m.nights for m in r.months)
    cd = (await session.execute(select(CalendarDay).where(CalendarDay.date == day(40)))).scalar_one()
    assert cd.units_available == 0
    logs = (await session.execute(select(AvailabilityChangeLog))).scalars().all()
    assert logs and all(log.new_units_available == 0 for log in logs)


async def test_noches_con_precio_pero_cerradas_se_avisan(session):
    prop, unit = await _seed(session)
    cm = FakeCM()
    for i in (5, 6, 7):
        cm.cal[day(i)] = (D("300000"), 0)  # con precio, cerradas
    session.add(CalendarDay(unit_type_id=unit.id, date=day(6), units_available=0, is_blocked=True))
    for i in (5, 7):
        session.add(CalendarDay(unit_type_id=unit.id, date=day(i), units_available=0))
    await session.flush()
    p = await ext.preview(session, cm, ExtensionParams(unit_type_id=unit.id, until=day(60)), today=TODAY)
    assert p.closed_priced == 2 and p.first_closed_priced == day(5)  # la bloqueada por el host no cuenta
    s = await ext.status(session, unit.id, today=TODAY)
    assert s.closed_nights == 2 and s.first_closed_night == day(5)


async def test_tramos_agrupados_por_precio_y_apertura(session):
    prop, unit = await _seed(session)
    cm = FakeCM()
    params = ExtensionParams(unit_type_id=unit.id, until=date(2036, 11, 30), weekend_pct=D("10"))
    p = await ext.preview(session, cm, params, today=TODAY)
    await ext.apply(session, cm, params, p.fingerprint, today=TODAY)
    [entries] = cm.writes
    # 7 nov 2036 es viernes: el primer tramo es el fin de semana (vie+sáb) con +10 %
    assert entries[0] == CalendarEntry(date(2036, 11, 7), date(2036, 11, 8), D("330000"), 1)
    assert all(e.num_avail == 1 for e in entries)
    assert sum((e.date_to - e.date_from).days + 1 for e in entries) == p.total_nights
    for a, b in zip(entries, entries[1:]):
        assert a.price != b.price or a.date_to + timedelta(days=1) != b.date_from


async def test_estado_del_horizonte(session):
    prop, unit = await _seed(session)
    s = await ext.status(session, unit.id, today=TODAY)
    assert s.first_unpriced_night == day(PRICED) and s.needs_extension and s.months_covered == 0
    # una reserva sin precio cargado no es un hueco
    session.add(Booking(unit_type_id=unit.id, channel_kind=ChannelKind.airbnb, check_in=day(PRICED),
                        check_out=day(PRICED + 2), status=BookingStatus.confirmed))
    await session.flush()
    s = await ext.status(session, unit.id, today=TODAY)
    assert s.first_unpriced_night == day(PRICED + 2)
    for i in range(PRICED + 2, 400):
        session.add(Rate(unit_type_id=unit.id, date=day(i), base_price=D("300000")))
    await session.flush()
    s = await ext.status(session, unit.id, today=TODAY)
    assert s.first_unpriced_night == day(400) and not s.needs_extension and s.months_covered == 13
    assert s.default_until == date(2038, 4, 8) and s.max_until == date(2038, 10, 8)


# --------- Precio 0 = sin precio (US4) ---------


async def test_precio_cero_es_sin_precio(session):
    prop, unit = await _seed(session)
    session.add(Rate(unit_type_id=unit.id, date=day(35), base_price=D("0")))
    await session.flush()
    assert await pricing_service.get_price(session, unit.id, day(35)) is None
    [view] = await pricing_app_service.get_calendar(session, unit.id, day(35), day(35))
    assert view.base_price is None and view.effective_price is None
    sugs = await suggestion_engine.generate_suggestions(
        session, unit_type_id=unit.id, date_from=day(35), date_to=day(35), today=TODAY
    )
    assert sugs == []


class FakeImportCM:
    def __init__(self, rates):
        self.properties = [RemoteProperty("337229", "Apto", "COP", [RemoteRoom("697411", "3BR", 1)])]
        self.rates = rates

    async def test_connection(self):
        return ConnectionInfo(True, self.properties)

    async def get_properties(self):
        return self.properties

    async def get_rates(self, room, df, dt):
        return self.rates

    async def get_bookings(self, prop, since=None):
        return []


async def test_import_no_guarda_precio_cero_y_corrige_basura(session):
    prop, unit = await _seed(session)
    session.add(Rate(unit_type_id=unit.id, date=day(36), base_price=D("0")))
    await session.flush()
    cm = FakeImportCM([
        RemoteRate("697411", day(35), D("0"), 0),
        RemoteRate("697411", day(36), D("320000"), 1),
    ])
    run = await sync_service.import_remote(session, cm, day(35), day(36))
    assert run.issue_count == 0
    assert await _count(session, Rate, Rate.date == day(35)) == 0
    assert await pricing_service.get_price(session, unit.id, day(36)) == D("320000")


# --------- Adaptador V2 ---------


async def test_adaptador_v2_un_post_y_una_relectura(monkeypatch):
    calls: list = []
    a = Beds24V2Adapter(refresh_token="x", prop_id="337229", room_id="697411", base_url="http://b24")

    async def fake_request(method, path, params=None, json_body=None):
        calls.append((method, path, json_body))
        if method == "POST":
            return [{"success": True}]
        return {"data": [{"roomId": 697411, "calendar": [
            {"from": "2037-03-01", "to": "2037-03-05", "numAvail": 1, "price1": 300000},
            {"from": "2037-03-06", "to": "2037-03-06", "numAvail": 0, "price1": 330000},
        ]}]}

    monkeypatch.setattr(a, "_request", fake_request)
    entries = [
        CalendarEntry(date(2037, 3, 1), date(2037, 3, 5), D("300000"), 1),
        CalendarEntry(date(2037, 3, 6), date(2037, 3, 6), D("330000"), None),
    ]
    res = await a.set_calendar_entries("697411", entries)
    assert res.ok and res.verified
    assert [c[0] for c in calls] == ["POST", "GET"]
    body = calls[0][2][0]["calendar"]
    assert body[0] == {"from": "2037-03-01", "to": "2037-03-05", "price1": 300000.0, "numAvail": 1}
    assert "numAvail" not in body[1]
    # disponibilidad distinta pero precio OK → verificado con aviso
    entries[0] = CalendarEntry(date(2037, 3, 1), date(2037, 3, 5), D("300000"), 0)
    res = await a.set_calendar_entries("697411", entries)
    assert res.verified and "apertura" in (res.detail or "") and res.unconfirmed == 5
    entries[0] = CalendarEntry(date(2037, 3, 1), date(2037, 3, 5), D("300000"), 1)
    # si la relectura no coincide → no verificado
    entries[1] = CalendarEntry(date(2037, 3, 6), date(2037, 3, 6), D("340000"), None)
    assert (await a.set_calendar_entries("697411", entries)).verified is False
    await a.aclose()


# --------- Rutas ---------


@pytest_asyncio.fixture
async def client(session, monkeypatch):
    holder = {"cm": FakeCM()}

    def _override_adapter(*_a, **_k):
        return holder["cm"]

    async def _override():
        yield session

    monkeypatch.setattr(pricing_routes, "get_adapter", _override_adapter)
    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.holder = holder
        yield c
    app.dependency_overrides.pop(get_session, None)


async def test_rutas(client, session):
    prop, unit = await _seed(session)
    await session.commit()
    today = date.today()
    cm = FakeCM()
    cm.cal = {today + timedelta(days=i): ((D("300000"), 1) if i < 30 else (D("0"), 0)) for i in range(800)}
    client.holder["cm"] = cm

    st = (await client.get("/pricing/extension/status", params={"unit_type_id": unit.id})).json()
    assert st["needs_extension"] is True

    body = {"unit_type_id": unit.id, "until": str(today + timedelta(days=60))}
    pv = await client.post("/pricing/extension/preview", json=body)
    assert pv.status_code == 200
    data = pv.json()
    assert data["total_nights"] == 31 and "items" not in data["months"][0]

    assert (await client.post("/pricing/extension/preview",
                              json={**body, "until": str(today + timedelta(days=900))})).status_code == 422
    assert (await client.post("/pricing/extension/apply",
                              json={**body, "fingerprint": "nope"})).status_code == 409
    ap = await client.post("/pricing/extension/apply", json={**body, "fingerprint": data["fingerprint"]})
    assert ap.status_code == 200 and ap.json()["applied_nights"] == 31


class _Beds24Like:
    """Imita a Beds24 (2026-10-09): guarda el valor de calendario y, aparte, el inventario
    efectivo. Un `numAvail` igual al valor de calendario se ignora (sin "modified")."""

    def __init__(self, days, cal_value=1, inventory=0):
        self.cal = {d: cal_value for d in days}
        self.inv = {d: inventory for d in days}
        self.price = {d: 300000.0 for d in days}
        self.posts: list = []

    async def request(self, method, path, params=None, json_body=None):
        if method == "POST":
            self.posts.append(json_body[0]["calendar"])
            for item in json_body[0]["calendar"]:
                d, end = date.fromisoformat(item["from"]), date.fromisoformat(item["to"])
                while d <= end:
                    if "price1" in item:
                        self.price[d] = item["price1"]
                    if "numAvail" in item and item["numAvail"] != self.cal[d]:
                        self.cal[d] = self.inv[d] = item["numAvail"]
                    d += timedelta(days=1)
            return [{"success": True}]
        start, end = date.fromisoformat(params["startDate"]), date.fromisoformat(params["endDate"])
        cal, d = [], start
        while d <= end:
            cal.append({"from": d.isoformat(), "to": d.isoformat(), "numAvail": self.inv[d], "price1": self.price[d]})
            d += timedelta(days=1)
        return {"data": [{"roomId": 697411, "calendar": cal}]}


async def test_adaptador_fuerza_apertura_ignorada(monkeypatch):
    days = [date(2037, 3, 1) + timedelta(days=i) for i in range(10)]
    fake = _Beds24Like(days)
    a = Beds24V2Adapter(refresh_token="x", prop_id="337229", room_id="697411", base_url="http://b24")
    monkeypatch.setattr(a, "_request", fake.request)
    res = await a.set_calendar_entries(
        "697411", [CalendarEntry(date(2037, 3, 1), date(2037, 3, 5), D("340000"), 1)]
    )
    assert res.verified and res.unconfirmed == 0 and res.detail is None
    assert [p[0].get("numAvail") for p in fake.posts] == [1, 0, 1]  # escritura, 0, 1
    assert all(fake.inv[d] == 1 for d in days[:5]) and fake.inv[days[6]] == 0

    # Calendario → Abrir (set_availability_range) también se fuerza
    r = await a.set_availability_range("697411", days[6], days[7], 1)
    assert r.verified and fake.inv[days[6]] == 1
    # Bloquear (0) nunca pasa por "abrir"
    fake.posts.clear()
    r = await a.set_availability_range("697411", days[8], days[9], 0)
    assert r.verified and [p[0]["numAvail"] for p in fake.posts] == [0]
    await a.aclose()
