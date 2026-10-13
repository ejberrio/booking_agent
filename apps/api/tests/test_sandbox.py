"""Feature 026 — ambiente de pruebas (CHANNEL_MODE=simulated): nunca toca Beds24 ni teléfonos."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.channels import factory
from app.channels.simulated import SimulatedChannelAdapter
from app.core.config import settings
from app.db.session import get_session
from app.schemas.pricing import RangeSelection
from app.main import app
from app.models.booking import Booking
from app.models.calendar import CalendarDay
from app.models.enums import BookingStatus, ChangeOrigin, ChannelKind
from app.models.property import Property, UnitType
from app.services import pricing_app_service, pricing_service, push_service, sync_service

pytestmark = pytest.mark.anyio

TODAY = date.today()
D1 = TODAY + timedelta(days=5)


@pytest.fixture(autouse=True)
def _sandbox(monkeypatch):
    monkeypatch.setattr(settings, "channel_mode", "simulated")


async def _seed(session):
    prop = Property(name="Casa", city="Medellín", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    for i in range(3):
        await pricing_service.set_base_price(
            session, unit_type_id=unit.id, day=D1 + timedelta(days=i),
            new_price=Decimal("300000"), origin=ChangeOrigin.manual,
        )
        session.add(CalendarDay(unit_type_id=unit.id, date=D1 + timedelta(days=i),
                                units_available=1))
    session.add(Booking(unit_type_id=unit.id, channel_kind=ChannelKind.airbnb, check_in=D1,
                        check_out=D1 + timedelta(days=1), status=BookingStatus.confirmed,
                        external_ref="900"))
    await session.commit()
    return unit


async def test_adaptador_simulado_lee_la_base_y_no_envia_nada(session, monkeypatch):
    unit = await _seed(session)
    # Si algo intentara construir el adaptador real de Beds24, la prueba falla.
    import app.channels.beds24_v2 as v2

    def _boom(*a, **k):
        raise AssertionError("se construyó el adaptador REAL en modo simulado")

    monkeypatch.setattr(v2.Beds24V2Adapter, "__init__", _boom)
    adapter = factory.get_adapter(session)
    assert isinstance(adapter, SimulatedChannelAdapter) and factory.has_credentials(session)

    props = await adapter.get_properties()
    assert [(p.external_id, [r.external_id for r in p.rooms]) for p in props] == [
        ("337229", ["697411"])
    ]
    rates = await adapter.get_rates("697411", D1, D1 + timedelta(days=4))
    assert [r.price for r in rates] == [Decimal("300000")] * 3
    assert [b.external_id for b in await adapter.get_bookings("337229")] == ["900"]

    # Sincronizar contra el simulado no cambia nada.
    run = await sync_service.import_remote(session, adapter, TODAY, TODAY + timedelta(days=30))
    await session.commit()
    assert run.status.value in ("success", "partial")
    refs = [b.external_ref for b in (await session.execute(select(Booking))).scalars()]
    assert refs == ["900"]

    # Aplicar un precio: se audita y guarda localmente; el "canal" lo acepta sin enviarlo.
    sel = RangeSelection(D1, D1)
    prev = await pricing_app_service.preview_range(
        session, unit_type_id=unit.id, selection=sel, price=Decimal("350000")
    )
    res = await pricing_app_service.apply_range(
        session, adapter, unit_type_id=unit.id, selection=sel, price=Decimal("350000"),
        fingerprint=prev.fingerprint,
    )
    assert res.applied_days == [D1]
    assert await pricing_service.get_price(session, unit.id, D1) == Decimal("350000")


async def test_sin_avisos_al_celular(session):
    await push_service.register_device(session, token="tok-real-del-host")
    assert push_service.get_sender() is None and push_service.configured() is False
    assert (await push_service.send_test(session))["configured"] is False


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def test_no_se_conecta_beds24_real(client):
    r = await client.post("/settings/secrets/beds24_refresh_token/invite", json={"code": "abc"})
    assert r.status_code == 409
