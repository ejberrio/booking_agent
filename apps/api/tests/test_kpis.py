"""KPIs del dashboard (issue #97): noches reservadas por canal y bloqueadas."""

from datetime import date

from app.models.booking import Booking
from app.models.calendar import CalendarDay
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Property, UnitType
from app.services import pricing_app_service

FROM = date(2026, 7, 1)
TO = date(2026, 7, 31)


async def _seed(session):
    prop = Property(name="Apto", external_ref="337229")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="697411")
    session.add(unit)
    await session.flush()
    return unit


def _booking(unit_id, kind, check_in, check_out, status=BookingStatus.confirmed):
    return Booking(
        unit_type_id=unit_id, channel_kind=kind, check_in=check_in, check_out=check_out, status=status
    )


async def test_kpis_sin_datos(session):
    unit = await _seed(session)
    out = await pricing_app_service.get_kpis(session, unit.id, FROM, TO)
    assert out["reserved_nights"] == {"booking": 0, "airbnb": 0, "direct": 0}
    assert out["total_reserved"] == 0
    assert out["blocked_nights"] == 0


async def test_noches_por_canal(session):
    unit = await _seed(session)
    session.add(_booking(unit.id, ChannelKind.booking, date(2026, 7, 10), date(2026, 7, 13)))  # 3
    session.add(_booking(unit.id, ChannelKind.booking, date(2026, 7, 20), date(2026, 7, 22)))  # 2
    session.add(_booking(unit.id, ChannelKind.airbnb, date(2026, 7, 5), date(2026, 7, 9)))  # 4
    await session.flush()
    out = await pricing_app_service.get_kpis(session, unit.id, FROM, TO)
    assert out["reserved_nights"] == {"booking": 5, "airbnb": 4, "direct": 0}
    assert out["total_reserved"] == 9


async def test_reserva_que_cruza_los_bordes_del_mes(session):
    unit = await _seed(session)
    # Entra el 29 de junio y sale el 3 de julio: solo cuentan las noches 1 y 2 de julio.
    session.add(_booking(unit.id, ChannelKind.booking, date(2026, 6, 29), date(2026, 7, 3)))
    # Entra el 30 de julio y sale el 2 de agosto: cuentan las noches 30 y 31.
    session.add(_booking(unit.id, ChannelKind.airbnb, date(2026, 7, 30), date(2026, 8, 2)))
    await session.flush()
    out = await pricing_app_service.get_kpis(session, unit.id, FROM, TO)
    assert out["reserved_nights"]["booking"] == 2
    assert out["reserved_nights"]["airbnb"] == 2


async def test_canceladas_y_otros_units_no_cuentan(session):
    unit = await _seed(session)
    session.add(
        _booking(
            unit.id,
            ChannelKind.booking,
            date(2026, 7, 10),
            date(2026, 7, 12),
            status=BookingStatus.cancelled,
        )
    )
    other = UnitType(property_id=unit.property_id, name="Otro", external_ref="X")
    session.add(other)
    await session.flush()
    session.add(_booking(other.id, ChannelKind.airbnb, date(2026, 7, 10), date(2026, 7, 12)))
    await session.flush()
    out = await pricing_app_service.get_kpis(session, unit.id, FROM, TO)
    assert out["total_reserved"] == 0


async def test_noches_bloqueadas_en_rango(session):
    unit = await _seed(session)
    for d in (date(2026, 7, 6), date(2026, 10, 19)):  # la de octubre queda fuera del rango
        session.add(CalendarDay(unit_type_id=unit.id, date=d, units_available=0, is_blocked=True))
    session.add(
        CalendarDay(unit_type_id=unit.id, date=date(2026, 7, 7), units_available=1, is_blocked=False)
    )
    await session.flush()
    out = await pricing_app_service.get_kpis(session, unit.id, FROM, TO)
    assert out["blocked_nights"] == 1
