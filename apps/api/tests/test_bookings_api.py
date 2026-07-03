"""Feature 016: GET /bookings (rango) y CRUD /calendar-notes."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import pytest_asyncio

from app.db.session import get_session
from app.main import app
from app.models.booking import Booking
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Property, UnitType

pytestmark = pytest.mark.anyio


@pytest_asyncio.fixture
async def client(session):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


async def _seed(session):
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    session.add(
        Booking(
            unit_type_id=unit.id,
            channel_kind=ChannelKind.booking,
            check_in=date(2026, 8, 6),
            check_out=date(2026, 8, 19),
            status=BookingStatus.confirmed,
            external_ref="75333844",
            guest_name="John Doe",
        )
    )
    session.add(
        Booking(
            unit_type_id=unit.id,
            channel_kind=ChannelKind.airbnb,
            check_in=date(2026, 8, 20),
            check_out=date(2026, 8, 22),
            status=BookingStatus.cancelled,
            external_ref="CANC-1",
        )
    )
    await session.flush()
    return unit


async def test_bookings_por_rango(client, session):
    unit = await _seed(session)
    res = await client.get(
        "/bookings",
        params={"unit_type_id": unit.id, "date_from": "2026-08-01", "date_to": "2026-08-31"},
    )
    assert res.status_code == 200
    bookings = res.json()["bookings"]
    assert len(bookings) == 1  # la cancelada queda fuera
    b = bookings[0]
    assert b["guest_name"] == "John Doe"
    assert b["channel"] == "booking"
    assert b["nights"] == 13
    assert b["external_ref"] == "75333844"


async def test_bookings_borde_checkout_no_solapa(client, session):
    unit = await _seed(session)
    # rango que empieza el día del checkout: la noche del 19 no es de esa reserva
    res = await client.get(
        "/bookings",
        params={"unit_type_id": unit.id, "date_from": "2026-08-19", "date_to": "2026-08-25"},
    )
    assert res.json()["bookings"] == []
    # rango que termina justo la primera noche sí solapa
    res2 = await client.get(
        "/bookings",
        params={"unit_type_id": unit.id, "date_from": "2026-08-01", "date_to": "2026-08-06"},
    )
    assert len(res2.json()["bookings"]) == 1


async def test_bookings_sin_nombre(client, session):
    unit = await _seed(session)
    session.add(
        Booking(
            unit_type_id=unit.id,
            channel_kind=ChannelKind.direct,
            check_in=date(2026, 9, 1),
            check_out=date(2026, 9, 3),
            status=BookingStatus.confirmed,
        )
    )
    await session.flush()
    res = await client.get(
        "/bookings",
        params={"unit_type_id": unit.id, "date_from": "2026-09-01", "date_to": "2026-09-02"},
    )
    assert res.json()["bookings"][0]["guest_name"] is None


# --- notas ------------------------------------------------------------------


async def test_notas_crud_completo(client, session):
    unit = await _seed(session)
    res = await client.post(
        "/calendar-notes",
        json={
            "unit_type_id": unit.id,
            "date_from": "2026-10-19",
            "date_to": "2026-10-21",
            "text": "Reserva personal de Fulano",
        },
    )
    assert res.status_code == 200
    note = res.json()
    assert note["text"] == "Reserva personal de Fulano"

    # día único + solape permitido
    res2 = await client.post(
        "/calendar-notes",
        json={
            "unit_type_id": unit.id,
            "date_from": "2026-10-20",
            "date_to": "2026-10-20",
            "text": "Llevar llaves",
        },
    )
    assert res2.status_code == 200

    listing = (
        await client.get("/calendar-notes", params={"unit_type_id": unit.id})
    ).json()["notes"]
    assert len(listing) == 2

    upd = await client.patch(
        f"/calendar-notes/{note['id']}", json={"text": "Reserva personal de Mengano"}
    )
    assert upd.status_code == 200 and upd.json()["text"] == "Reserva personal de Mengano"
    assert upd.json()["date_from"] == "2026-10-19"  # el resto no cambia

    dele = await client.delete(f"/calendar-notes/{note['id']}")
    assert dele.json() == {"deleted": True}
    assert (await client.delete(f"/calendar-notes/{note['id']}")).status_code == 404


@pytest.mark.parametrize(
    "body_extra",
    [
        {"text": "   "},  # vacío tras strip
        {"text": "x" * 501},  # demasiado largo
        {"text": "ok", "date_from": "2026-10-21", "date_to": "2026-10-19"},  # invertidas
    ],
)
async def test_notas_validaciones_422(client, session, body_extra):
    unit = await _seed(session)
    body = {
        "unit_type_id": unit.id,
        "date_from": "2026-10-19",
        "date_to": "2026-10-21",
        "text": "ok",
    }
    body.update(body_extra)
    res = await client.post("/calendar-notes", json=body)
    assert res.status_code == 422
