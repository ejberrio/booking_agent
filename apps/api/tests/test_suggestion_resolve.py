"""Feature 014 · US1: acción única "Aprobar y aplicar" (T004).

Servicio (intelligence_service.apply_suggestion reforzado + reject ampliado) y
endpoints /suggestions con el patrón ASGITransport de test_channel_offsets_api.
"""

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
from app.models.enums import ChannelKind, SuggestionStatus, SyncIssueKind
from app.models.market import PriceSuggestion
from app.models.property import Channel, Property, UnitType
from app.models.sync import SyncIssue
from app.services import intelligence_service, pricing_service, suggestion_service
from app.services.intelligence_service import SuggestionPublishError, SuggestionStateError

pytestmark = pytest.mark.anyio

D = Decimal
TODAY = date.today()
F1 = TODAY + timedelta(days=30)
F3 = TODAY + timedelta(days=32)


class FakeCM:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.published: list = []

    async def set_rate_range(self, room, df, dt, price):
        if self.fail:
            raise ChannelError("canal caído")
        self.published.append((room, df, dt, price))
        return WriteResult(True, True)

    async def aclose(self):
        return None


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def _seed(session, *, date_from=F1, date_to=F3, status=SuggestionStatus.proposed):
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
    await session.flush()
    day = date_from
    while day <= date_to:
        await pricing_service.set_base_price(
            session, unit_type_id=unit.id, day=day, new_price=D("300000")
        )
        day += timedelta(days=1)
    sug = PriceSuggestion(
        property_id=prop.id,
        unit_type_id=unit.id,
        date_from=date_from,
        date_to=date_to,
        suggested_price=D("380000"),
        rationale={"text": "evento cercano"},
        confidence=D("0.8"),
        status=status,
    )
    session.add(sug)
    await session.flush()
    return unit, sug


# --- servicio: apply -----------------------------------------------------------


async def test_apply_proposed_publica_y_audita(session):
    unit, sug = await _seed(session)
    cm = FakeCM()
    applied, applied_from, issues = await intelligence_service.apply_suggestion(
        session, cm, sug.id
    )
    assert applied.status is SuggestionStatus.applied
    assert applied.applied_change_id is not None
    assert applied_from == sug.date_from
    assert issues == 0
    assert cm.published  # publicado al canal
    assert await pricing_service.get_price(session, unit.id, F1) == D("380000")


async def test_apply_approved_historica(session):
    unit, sug = await _seed(session, status=SuggestionStatus.approved)
    applied, _, _ = await intelligence_service.apply_suggestion(session, FakeCM(), sug.id)
    assert applied.status is SuggestionStatus.applied


@pytest.mark.parametrize("estado", [SuggestionStatus.applied, SuggestionStatus.rejected])
async def test_apply_resuelta_conflicto_sin_efectos(session, estado):
    unit, sug = await _seed(session, status=estado)
    cm = FakeCM()
    with pytest.raises(SuggestionStateError) as exc:
        await intelligence_service.apply_suggestion(session, cm, sug.id)
    assert estado.value in str(exc.value)
    assert cm.published == []  # CERO llamadas al canal
    assert await pricing_service.get_price(session, unit.id, F1) == D("300000")


async def test_apply_recorta_dias_pasados(session):
    d0, d2 = TODAY - timedelta(days=1), TODAY + timedelta(days=1)
    unit, sug = await _seed(session, date_from=d0, date_to=d2)
    _, applied_from, _ = await intelligence_service.apply_suggestion(session, FakeCM(), sug.id)
    assert applied_from == TODAY
    # ayer intacto; hoy y mañana con el precio sugerido
    assert await pricing_service.get_price(session, unit.id, d0) == D("300000")
    assert await pricing_service.get_price(session, unit.id, TODAY) == D("380000")
    assert await pricing_service.get_price(session, unit.id, d2) == D("380000")


async def test_apply_vencida_total(session):
    unit, sug = await _seed(
        session, date_from=TODAY - timedelta(days=5), date_to=TODAY - timedelta(days=3)
    )
    cm = FakeCM()
    with pytest.raises(SuggestionStateError, match="venció"):
        await intelligence_service.apply_suggestion(session, cm, sug.id)
    assert cm.published == []
    assert sug.status is SuggestionStatus.proposed


async def test_apply_canal_caido_no_marca_aplicada(session):
    unit, sug = await _seed(session)
    with pytest.raises(SuggestionPublishError):
        await intelligence_service.apply_suggestion(session, FakeCM(fail=True), sug.id)
    assert sug.status is SuggestionStatus.proposed
    assert sug.applied_change_id is None


# --- servicio: reject ----------------------------------------------------------


async def test_reject_approved_historica(session):
    unit, sug = await _seed(session, status=SuggestionStatus.approved)
    s = await suggestion_service.reject(session, sug.id)
    assert s.status is SuggestionStatus.rejected


async def test_reject_aplicada_conflicto(session):
    unit, sug = await _seed(session, status=SuggestionStatus.applied)
    with pytest.raises(ValueError, match="applied"):
        await suggestion_service.reject(session, sug.id)


# --- endpoints -----------------------------------------------------------------


@pytest.fixture()
def fake_cm(monkeypatch):
    cm = FakeCM()
    monkeypatch.setattr(suggestion_routes, "get_adapter", lambda: cm)
    return cm


async def test_endpoint_list_pending_y_current_price(client, session, fake_cm):
    unit, sug = await _seed(session)
    otra = PriceSuggestion(
        property_id=sug.property_id,
        unit_type_id=unit.id,
        date_from=F1,
        date_to=F1,
        suggested_price=D("350000"),
        status=SuggestionStatus.approved,
    )
    session.add(otra)
    await session.flush()

    res = await client.get("/suggestions", params={"pending": "true"})
    assert res.status_code == 200
    data = res.json()
    assert {s["status"] for s in data} == {"proposed", "approved"}
    assert data[0]["current_price"] == "300000.00"

    solo = await client.get("/suggestions", params={"status": "proposed"})
    assert [s["status"] for s in solo.json()] == ["proposed"]


async def test_endpoint_apply_ok_y_doble_aplicacion_409(client, session, fake_cm):
    unit, sug = await _seed(session)
    res = await client.post(f"/suggestions/{sug.id}/apply")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "applied"
    assert body["applied_from"] == F1.isoformat()
    assert body["publish_issues"] == 0

    n_logs = (
        await session.execute(select(func.count()).select_from(PriceChangeLog))
    ).scalar_one()
    dup = await client.post(f"/suggestions/{sug.id}/apply")
    assert dup.status_code == 409
    assert "applied" in dup.json()["detail"]
    n_logs2 = (
        await session.execute(select(func.count()).select_from(PriceChangeLog))
    ).scalar_one()
    assert n_logs2 == n_logs  # sin segundo cambio de precio (SC-004)


async def test_endpoint_apply_canal_caido_502_con_incidencia(client, session, monkeypatch):
    unit, sug = await _seed(session)
    sug_id, unit_id = sug.id, unit.id
    await session.commit()  # como en producción: la sugerencia ya existe commiteada
    monkeypatch.setattr(suggestion_routes, "get_adapter", lambda: FakeCM(fail=True))
    res = await client.post(f"/suggestions/{sug_id}/apply")
    assert res.status_code == 502
    issues = (
        (await session.execute(select(SyncIssue).where(SyncIssue.kind == SyncIssueKind.comm_error)))
        .scalars()
        .all()
    )
    assert any(f"suggestion:{sug_id}" == i.entity_ref for i in issues)
    fresh = await session.get(PriceSuggestion, sug_id)
    assert fresh.status is SuggestionStatus.proposed
    assert await pricing_service.get_price(session, unit_id, F1) == D("300000")  # rollback local


async def test_endpoint_approve_retirado(client, session, fake_cm):
    unit, sug = await _seed(session)
    res = await client.post(f"/suggestions/{sug.id}/approve")
    assert res.status_code in (404, 405)


async def test_superseded_no_se_aplica_ni_rechaza(session):
    unit, sug = await _seed(session, status=SuggestionStatus.superseded)
    cm = FakeCM()
    with pytest.raises(SuggestionStateError, match="superseded"):
        await intelligence_service.apply_suggestion(session, cm, sug.id)
    assert cm.published == []
    with pytest.raises(ValueError, match="superseded"):
        await suggestion_service.reject(session, sug.id)


async def test_superseded_fuera_de_pendientes(client, session, fake_cm):
    unit, sug = await _seed(session, status=SuggestionStatus.superseded)
    res = await client.get("/suggestions", params={"pending": "true"})
    assert res.json() == []
