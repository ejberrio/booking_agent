"""Feature 019: noches vendibles, bloques por API y aplicación en lote con vista previa única."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

import app.api.routes.suggestions as suggestion_routes
from app.channels.base import WriteResult
from app.channels.errors import ChannelError
from app.db.session import get_session
from app.main import app
from app.models.audit import PriceChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay
from app.models.enums import BookingStatus, ChangeOrigin, ChannelKind, SuggestionStatus
from app.models.market import PriceSuggestion
from app.models.pricing import PricingRule
from app.models.property import Channel, Property, UnitType
from app.models.sync import SyncIssue
from app.services import pricing_service, suggestion_batch

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date.today()


def day(n: int) -> date:
    return TODAY + timedelta(days=n)


class FakeCM:
    """Canal falso: puede fallar con excepción o con incidencias para ciertos días."""

    def __init__(self, *, raise_on: set[date] | None = None):
        self.raise_on = raise_on or set()
        self.published: list = []

    async def set_rate_range(self, room, df, dt, price):
        if any(df <= d <= dt for d in self.raise_on):
            raise ChannelError("canal caído")
        self.published.append((df, dt, price))
        return WriteResult(True, True)

    async def aclose(self):
        return None


class BoomCM(FakeCM):
    """Excepción NO de canal (p. ej. bug de red): el tramo igual debe revertirse."""

    async def set_rate_range(self, room, df, dt, price):
        if any(df <= d <= dt for d in self.raise_on):
            raise RuntimeError("boom")
        return await super().set_rate_range(room, df, dt, price)


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def _unit(session, days=40, base="300000"):
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    await session.flush()
    for i in range(-3, days):
        await pricing_service.set_base_price(
            session, unit_type_id=unit.id, day=day(i), new_price=D(base)
        )
    await session.flush()
    return prop, unit


async def _sug(session, prop, unit, d1, d2, price="380000", factors=None, status=SuggestionStatus.proposed):
    s = PriceSuggestion(
        property_id=prop.id, unit_type_id=unit.id, date_from=d1, date_to=d2,
        suggested_price=D(price), status=status,
        rationale={"text": "x", "factors": factors or []}, confidence=D("0.7"),
    )
    session.add(s)
    await session.flush()
    return s


async def _book(session, unit, ci, co, status=BookingStatus.confirmed):
    b = Booking(unit_type_id=unit.id, channel_kind=ChannelKind.booking, check_in=ci, check_out=co, status=status)
    session.add(b)
    await session.flush()
    return b


def _ev(name):
    return [{"kind": "event", "label": name, "event": {"name": name}}]


# --- US1: noches vendibles -------------------------------------------------------


async def test_vendibles_reserva_bloqueo_inventario_y_pasadas(session):
    prop, unit = await _unit(session)
    s = await _sug(session, prop, unit, day(-2), day(6))
    await _book(session, unit, day(1), day(3))  # ocupa 1 y 2; el 3 es salida (vendible)
    await _book(session, unit, day(4), day(5), status=BookingStatus.cancelled)  # no ocupa
    session.add(CalendarDay(unit_type_id=unit.id, date=day(5), units_available=1, is_blocked=True))
    session.add(CalendarDay(unit_type_id=unit.id, date=day(6), units_available=0))
    await session.flush()

    occ = await suggestion_batch.occupied_nights(session, unit.id, day(0), day(6))
    assert occ == {day(1): "reservada", day(2): "reservada", day(5): "bloqueada", day(6): "reservada"}

    [v] = await suggestion_batch.pending_views(session, today=TODAY)
    assert v.suggestion.id == s.id
    assert [n.date for n in v.nights] == [day(0), day(3), day(4)]
    assert v.total_nights == 7 and v.occupied_count == 4  # pasadas excluidas del total


async def test_sugerencia_totalmente_ocupada_sin_noches(session):
    prop, unit = await _unit(session)
    await _sug(session, prop, unit, day(10), day(11))
    await _book(session, unit, day(10), day(12))
    [v] = await suggestion_batch.pending_views(session, today=TODAY)
    assert v.nights == [] and v.occupied_count == 2


async def test_blocks_api_oculta_ocupadas_y_reaparecen_al_cancelar(session, client):
    prop, unit = await _unit(session)
    a = await _sug(session, prop, unit, day(10), day(12), factors=_ev("Juanes"))
    b = await _sug(session, prop, unit, day(20), day(20), factors=_ev("Chayanne"))
    booking = await _book(session, unit, day(20), day(21))  # oculta b por completo
    await _book(session, unit, day(11), day(12))  # recorta a
    await session.commit()

    body = (await client.get("/suggestions/blocks")).json()
    assert [blk["title"] for blk in body["blocks"]] == ["Juanes"]
    juanes = body["blocks"][0]
    assert [n["date"] for n in juanes["nights"]] == [day(10).isoformat(), day(12).isoformat()]
    assert juanes["suggestions"][0]["occupied_count"] == 1
    assert juanes["direction"] == "up"
    assert body["hidden_occupied"] == 2

    # La reserva de Chayanne se cancela (sync) → reaparece sin correr el scan.
    booking.status = BookingStatus.cancelled
    await session.commit()
    body = (await client.get("/suggestions/blocks")).json()
    assert [blk["title"] for blk in body["blocks"]] == ["Juanes", "Chayanne"]
    assert a.id in body["blocks"][0]["suggestion_ids"] and b.id in body["blocks"][1]["suggestion_ids"]


# --- US2: vista previa y aplicación en lote ---------------------------------------


async def test_preview_omisiones_con_motivo(session):
    prop, unit = await _unit(session)
    session.add(PricingRule(property_id=prop.id, min_price=D("200000"), max_price=D("400000"), is_active=True))
    ok = await _sug(session, prop, unit, day(-1), day(2))  # 1 pasada, 3 futuras
    caro = await _sug(session, prop, unit, day(5), day(5), price="900000")  # fuera de límites
    resuelta = await _sug(session, prop, unit, day(7), day(7), status=SuggestionStatus.applied)
    await _book(session, unit, day(1), day(2))
    p = await suggestion_batch.preview_batch(session, [ok.id, caro.id, resuelta.id], today=TODAY)
    reasons = {(i.date, i.suggestion_id): i.reason for i in p.items}
    assert reasons[(day(-1), ok.id)] == "pasada"
    assert reasons[(day(0), ok.id)] is None and reasons[(day(2), ok.id)] is None
    assert reasons[(day(1), ok.id)] == "reservada"
    assert reasons[(day(5), caro.id)] == "fuera de límites"
    assert reasons[(day(7), resuelta.id)] == "sugerencia resuelta"
    assert p.valid_count == 2 and p.skipped_count == 4
    old = {(i.date): i.old_price for i in p.items if i.suggestion_id == ok.id}
    assert old[day(0)] == D("300000")


async def test_preview_conflicto_misma_noche(session):
    prop, unit = await _unit(session)
    a = await _sug(session, prop, unit, day(3), day(4))
    b = await _sug(session, prop, unit, day(4), day(4), price="350000")
    p = await suggestion_batch.preview_batch(session, [a.id, b.id], today=TODAY)
    conflicts = [(i.date, i.suggestion_id) for i in p.items if i.reason == "conflicto"]
    assert sorted(conflicts) == sorted([(day(4), a.id), (day(4), b.id)])


async def test_huella_cambia_y_apply_stale_no_escribe(session):
    prop, unit = await _unit(session)
    s = await _sug(session, prop, unit, day(3), day(5))
    p = await suggestion_batch.preview_batch(session, [s.id], today=TODAY)

    # cambia un precio entre preview y apply
    await pricing_service.set_base_price(session, unit_type_id=unit.id, day=day(4), new_price=D("310000"))
    before = await session.scalar(select(func.count()).select_from(PriceChangeLog))
    cm = FakeCM()
    r = await suggestion_batch.apply_batch(session, cm, [s.id], p.fingerprint, today=TODAY)
    assert r.stale is True and cm.published == []
    assert await session.scalar(select(func.count()).select_from(PriceChangeLog)) == before

    # una reserva nueva también invalida la huella
    p2 = await suggestion_batch.preview_batch(session, [s.id], today=TODAY)
    await _book(session, unit, day(5), day(6))
    p3 = await suggestion_batch.preview_batch(session, [s.id], today=TODAY)
    assert p2.fingerprint != p3.fingerprint


async def test_apply_publica_audita_y_marca_aplicadas(session):
    prop, unit = await _unit(session)
    a = await _sug(session, prop, unit, day(3), day(4), price="380000")
    b = await _sug(session, prop, unit, day(5), day(5), price="320000")  # (022: las bajadas van como promoción)
    await _book(session, unit, day(4), day(5))  # omite el 4
    p = await suggestion_batch.preview_batch(session, [a.id, b.id], today=TODAY)
    cm = FakeCM()
    r = await suggestion_batch.apply_batch(session, cm, [a.id, b.id], p.fingerprint, today=TODAY)

    assert (r.applied_count, r.skipped_count, r.failed_count) == (2, 1, 0)
    assert r.suggestions == {a.id: "applied", b.id: "applied"}
    assert await pricing_service.get_price(session, unit.id, day(3)) == D("380000")
    assert await pricing_service.get_price(session, unit.id, day(4)) == D("300000")  # omitida
    assert await pricing_service.get_price(session, unit.id, day(5)) == D("320000")
    assert len(cm.published) == 2
    logs = (await session.execute(select(PriceChangeLog).where(PriceChangeLog.suggestion_id == a.id))).scalars().all()
    assert [lg.origin for lg in logs] == [ChangeOrigin.suggestion]
    await session.refresh(a)
    assert a.status is SuggestionStatus.applied and a.applied_change_id == logs[0].id


async def test_fallo_de_publicacion_revierte_solo_su_tramo(session):
    prop, unit = await _unit(session)
    a = await _sug(session, prop, unit, day(3), day(4), price="380000")
    b = await _sug(session, prop, unit, day(8), day(8), price="390000")
    p = await suggestion_batch.preview_batch(session, [a.id, b.id], today=TODAY)
    r = await suggestion_batch.apply_batch(
        session, FakeCM(raise_on={day(8)}), [a.id, b.id], p.fingerprint, today=TODAY
    )
    assert r.suggestions == {a.id: "applied", b.id: "pending"}
    assert [n.status for n in r.nights if n.suggestion_id == b.id] == ["failed"]
    # el tramo fallido no deja precio local distinto del canal
    assert await pricing_service.get_price(session, unit.id, day(8)) == D("300000")
    assert await pricing_service.get_price(session, unit.id, day(3)) == D("380000")
    await session.refresh(b)
    assert b.status is SuggestionStatus.proposed
    issues = (await session.execute(select(SyncIssue).where(SyncIssue.entity_ref.like("suggestion-batch:%")))).scalars().all()
    assert len(issues) == 1


async def test_excepcion_inesperada_del_canal_tambien_revierte(session):
    prop, unit = await _unit(session)
    a = await _sug(session, prop, unit, day(3), day(3), price="380000")
    p = await suggestion_batch.preview_batch(session, [a.id], today=TODAY)
    r = await suggestion_batch.apply_batch(
        session, BoomCM(raise_on={day(3)}), [a.id], p.fingerprint, today=TODAY
    )
    assert r.failed_count == 1 and r.suggestions == {a.id: "pending"}
    assert await pricing_service.get_price(session, unit.id, day(3)) == D("300000")


async def test_rutas_batch_preview_apply_y_409(session, client, monkeypatch):
    prop, unit = await _unit(session)
    a = await _sug(session, prop, unit, day(3), day(4))
    await session.commit()
    cm = FakeCM()
    monkeypatch.setattr(suggestion_routes, "get_adapter", lambda: cm)

    assert (await client.post("/suggestions/batch/preview", json={"suggestion_ids": []})).status_code == 422
    prev = (await client.post("/suggestions/batch/preview", json={"suggestion_ids": [a.id]})).json()
    assert prev["valid_count"] == 2 and len(prev["fingerprint"]) == 16

    bad = await client.post("/suggestions/batch/apply", json={"suggestion_ids": [a.id], "fingerprint": "x" * 16})
    assert bad.status_code == 409 and "revísala" in bad.json()["detail"]
    assert cm.published == []

    ok = await client.post("/suggestions/batch/apply", json={"suggestion_ids": [a.id], "fingerprint": prev["fingerprint"]})
    body = ok.json()
    assert ok.status_code == 200 and body["applied_count"] == 2
    assert body["suggestions"] == {str(a.id): "applied"}
