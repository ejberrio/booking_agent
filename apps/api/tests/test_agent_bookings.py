"""Feature 012: tool get_bookings con filtro y salida por canal (T013)."""

from __future__ import annotations

from datetime import date

from app.agent.tools import READ_TOOLS, exec_read
from app.models.booking import Booking
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Property, UnitType

DF, DT = "2026-08-01", "2026-08-31"


async def _seed(session) -> None:
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    session.add_all(
        [
            Booking(
                unit_type_id=unit.id,
                channel_kind=ChannelKind.booking,
                check_in=date(2026, 8, 6),
                check_out=date(2026, 8, 19),
                status=BookingStatus.confirmed,
                external_ref="bk-1",
            ),
            Booking(
                unit_type_id=unit.id,
                channel_kind=ChannelKind.airbnb,
                check_in=date(2026, 8, 20),
                check_out=date(2026, 8, 23),
                status=BookingStatus.confirmed,
                external_ref="ab-1",
            ),
            Booking(
                unit_type_id=unit.id,
                channel_kind=ChannelKind.direct,
                check_in=date(2026, 8, 25),
                check_out=date(2026, 8, 27),
                status=BookingStatus.confirmed,
                external_ref="dir-1",
            ),
        ]
    )
    await session.flush()


async def test_get_bookings_filters_by_channel(session):
    await _seed(session)
    out = await exec_read(
        session, "get_bookings", {"date_from": DF, "date_to": DT, "channel": "airbnb"}
    )
    assert [b["external_ref"] for b in out] == ["ab-1"]
    assert out[0]["channel"] == "airbnb"


async def test_get_bookings_without_filter_returns_all_with_channel(session):
    await _seed(session)
    out = await exec_read(session, "get_bookings", {"date_from": DF, "date_to": DT})
    assert [b["external_ref"] for b in out] == ["bk-1", "ab-1", "dir-1"]
    assert [b["channel"] for b in out] == ["booking", "airbnb", "direct"]


def test_get_bookings_schema_declares_channel_enum():
    spec = next(t for t in READ_TOOLS if t.name == "get_bookings")
    channel = spec.parameters["properties"]["channel"]
    assert channel["enum"] == ["booking", "airbnb", "direct"]
    assert "channel" not in spec.parameters["required"]


async def test_sync_calendar_tool(session, monkeypatch):
    """El chat puede disparar la sincronización entrante (cancelaciones, etc.)."""
    import app.agent.tools as tools_mod
    from app.channels.base import RemoteBooking, RemoteProperty, RemoteRate, RemoteRoom

    class FakeCM:
        async def get_properties(self):
            return [RemoteProperty("337229", "Apto", "COP", [RemoteRoom("697411", "3BR", 1)])]

        async def get_rates(self, room, df, dt):
            return [RemoteRate("697411", date(2026, 8, 6), 300000, 1)]

        async def get_bookings(self, prop, since=None):
            return [
                RemoteBooking(
                    external_id="bk-x", room_external_id="697411",
                    check_in=date(2026, 8, 6), check_out=date(2026, 8, 9),
                    status="cancelled", channel="booking",
                )
            ]

        async def aclose(self):
            return None

    monkeypatch.setattr(tools_mod, "get_adapter", lambda *_a, **_k: FakeCM())
    assert any(t.name == "sync_calendar" for t in READ_TOOLS)
    out = await exec_read(session, "sync_calendar", {})
    assert out["status"] == "success"
    assert out["created"] >= 1  # la cancelada se crea con su estado real (fix #91)
