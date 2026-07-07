"""Feature 015: registro de deals nativos (CRUD, solapes) y advertencia real de doble descuento."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio

from app.db.session import get_session
from app.main import app
from app.models.enums import ChannelKind
from app.services import native_deal_service as svc

pytestmark = pytest.mark.anyio

D = Decimal
JUL3, JUL10, JUL15, JUL31 = (
    date(2026, 7, 3),
    date(2026, 7, 10),
    date(2026, 7, 15),
    date(2026, 7, 31),
)


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


# --- CRUD (endpoints) -----------------------------------------------------------


async def test_crud_completo(client, session):
    # crear con fechas
    res = await client.post(
        "/pricing/native-deals",
        json={
            "channel": "booking",
            "name": "Vacaciones Julio · mín 3",
            "discount_pct": 20,
            "date_from": "2026-07-03",
            "date_to": "2026-07-31",
        },
    )
    assert res.status_code == 200
    deal = res.json()
    assert deal["channel"] == "booking" and deal["is_active"] is True

    # crear sin fechas (siempre activo)
    res2 = await client.post(
        "/pricing/native-deals",
        json={"channel": "airbnb", "name": "Descuento semanal", "discount_pct": 5},
    )
    assert res2.status_code == 200
    assert res2.json()["date_from"] is None and res2.json()["date_to"] is None

    # listar ordenado (booking antes que airbnb por orden del enum en BD; verificamos contenido)
    listing = (await client.get("/pricing/native-deals")).json()["deals"]
    assert {d["name"] for d in listing} == {"Vacaciones Julio · mín 3", "Descuento semanal"}

    # editar parcial: desactivar sin tocar el resto
    res3 = await client.patch(f"/pricing/native-deals/{deal['id']}", json={"is_active": False})
    assert res3.status_code == 200 and res3.json()["is_active"] is False
    assert res3.json()["name"] == "Vacaciones Julio · mín 3"

    # editar: abrir el extremo derecho con null explícito
    res4 = await client.patch(f"/pricing/native-deals/{deal['id']}", json={"date_to": None})
    assert res4.status_code == 200 and res4.json()["date_to"] is None

    # borrar
    res5 = await client.delete(f"/pricing/native-deals/{deal['id']}")
    assert res5.json() == {"deleted": True}
    assert (await client.delete(f"/pricing/native-deals/{deal['id']}")).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"channel": "direct", "name": "X", "discount_pct": 10},  # canal no gestionado
        {"channel": "expedia", "name": "X", "discount_pct": 10},  # canal desconocido
        {"channel": "booking", "name": "  ", "discount_pct": 10},  # nombre vacío
        {"channel": "booking", "name": "X", "discount_pct": 150},  # pct fuera de rango
        {  # fechas invertidas
            "channel": "booking",
            "name": "X",
            "discount_pct": 10,
            "date_from": "2026-07-31",
            "date_to": "2026-07-03",
        },
    ],
)
async def test_validaciones_422(client, session, body):
    res = await client.post("/pricing/native-deals", json=body)
    assert res.status_code == 422


# --- solape (servicio) ----------------------------------------------------------


async def _deal(session, *, channel=ChannelKind.booking, df=JUL3, dt=JUL31, active=True, name="Deal"):
    return await svc.create(
        session,
        channel=channel,
        name=name,
        discount_pct=D("20"),
        date_from=df,
        date_to=dt,
        is_active=active,
    )


async def test_solape_cerrado_y_sin_solape(session):
    await _deal(session)
    assert len(await svc.find_overlapping(session, JUL10, JUL15, None)) == 1
    assert await svc.find_overlapping(session, date(2026, 8, 1), date(2026, 8, 5), None) == []


async def test_solape_siempre_activo_y_medio_abiertos(session):
    await _deal(session, df=None, dt=None, name="Siempre")
    await _deal(session, df=None, dt=JUL15, name="HastaJul15")
    await _deal(session, df=JUL15, dt=None, name="DesdeJul15")
    nombres = {d.name for d in await svc.find_overlapping(session, date(2027, 1, 1), date(2027, 1, 5), None)}
    assert nombres == {"Siempre", "DesdeJul15"}  # HastaJul15 no llega a 2027
    nombres2 = {d.name for d in await svc.find_overlapping(session, JUL3, JUL10, None)}
    assert nombres2 == {"Siempre", "HastaJul15"}


async def test_solape_por_canal_y_inactivo(session):
    await _deal(session, channel=ChannelKind.booking, name="B")
    await _deal(session, channel=ChannelKind.airbnb, name="A")
    await _deal(session, channel=ChannelKind.booking, name="Off", active=False)
    solo_airbnb = await svc.find_overlapping(session, JUL10, JUL15, ["airbnb"])
    assert [d.name for d in solo_airbnb] == ["A"]
    todos = await svc.find_overlapping(session, JUL10, JUL15, None)
    assert {d.name for d in todos} == {"B", "A"}  # el inactivo nunca aparece


# --- advertencia real en el preview de promociones -------------------------------

from tests.test_offer_promotion_service import FakeCM as PromoFakeCM  # noqa: E402


async def _seed_promo_ctx(session):
    from app.models.calendar import Rate
    from app.models.property import Property, UnitType

    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    session.add(Rate(unit_type_id=unit.id, date=JUL10, base_price=D("350000")))
    await session.flush()
    return unit


async def test_preview_advierte_deal_concreto(session):
    from app.services import offer_promotion_service

    unit = await _seed_promo_ctx(session)
    await _deal(session, name="Vacaciones Julio · mín 3")
    prev = await offer_promotion_service.preview(
        session,
        PromoFakeCM(),
        unit_type_id=unit.id,
        first_night=JUL10,
        last_night=JUL15,
        name="Promo prueba",
        discount_pct=D("10"),
    )
    doble = [w for w in prev.warnings if "deal nativo" in w]
    assert len(doble) == 1
    assert "Vacaciones Julio · mín 3" in doble[0]
    assert "Booking.com" in doble[0] and "20%" in doble[0]


async def test_preview_sin_falsas_alarmas(session):
    from app.services import offer_promotion_service

    unit = await _seed_promo_ctx(session)
    await _deal(session, name="B-deal")  # booking jul 3-31
    await _deal(session, channel=ChannelKind.airbnb, name="Off", active=False, df=None, dt=None)

    # scope solo airbnb: el deal de booking no advierte; el de airbnb está inactivo
    prev = await offer_promotion_service.preview(
        session,
        PromoFakeCM(),
        unit_type_id=unit.id,
        first_night=JUL10,
        last_night=JUL15,
        name="Promo",
        discount_pct=D("10"),
        channels_scope=["airbnb"],
    )
    assert [w for w in prev.warnings if "deal nativo" in w] == []

    # fechas sin solape
    prev2 = await offer_promotion_service.preview(
        session,
        PromoFakeCM(),
        unit_type_id=unit.id,
        first_night=date(2026, 9, 1),
        last_night=date(2026, 9, 5),
        name="Promo",
        discount_pct=D("10"),
    )
    assert [w for w in prev2.warnings if "deal nativo" in w] == []


async def test_preview_sin_deals_identico(session):
    from app.services import offer_promotion_service

    unit = await _seed_promo_ctx(session)
    prev = await offer_promotion_service.preview(
        session,
        PromoFakeCM(),
        unit_type_id=unit.id,
        first_night=JUL10,
        last_night=JUL15,
        name="Promo",
        discount_pct=D("10"),
    )
    assert [w for w in prev.warnings if "deal nativo" in w] == []  # FR-010


async def test_preview_no_pisa_el_pct_de_la_promo(session):
    """Regresión: el bucle de warnings reutilizaba `pct` y devolvía el % del DEAL
    (siempre el último, p. ej. 25 del mensual) en lugar del % de la promoción."""
    from app.services import offer_promotion_service

    unit = await _seed_promo_ctx(session)
    await _deal(session, name="Semanal", channel=ChannelKind.airbnb, df=None, dt=None)
    prev = await offer_promotion_service.preview(
        session,
        PromoFakeCM(),
        unit_type_id=unit.id,
        first_night=JUL10,
        last_night=JUL15,
        name="Promo",
        discount_pct=D("10"),
    )
    assert any("deal nativo" in w for w in prev.warnings)  # el warning sigue
    assert prev.discount_pct == D("10")  # y el % de la promo NO se pisa
