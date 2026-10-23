"""Feature 042: rentabilidad mensual (renta corta frente a arriendo tradicional)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import httpx
import pytest
from sqlalchemy import select

from app.channels.beds24_v2 import _money
from app.models.booking import Booking
from app.models.calendar import Rate
from app.models.enums import BookingStatus, ChannelKind
from app.models.finance import FxRate
from app.models.property import Property, UnitType
from app.services import fx_service
from app.services import profitability_service as svc

pytestmark = pytest.mark.anyio

TODAY = date(2026, 10, 23)


def test_lee_valor_comision_y_moneda_de_beds24():
    airbnb = {"price": 385, "commission": 71.02,
              "rateDescription": "Base Price 357 USD\nCleaning fee 28.00 USD\nHost Fee -71.02 USD"}
    booking = {"price": 1120498, "commission": 171786,
               "rateDescription": "2026-10-09 (38711775 Standard Rate) COP 218592 genius"}
    assert _money(airbnb) == {"amount": D("385"), "commission": D("71.02"), "currency": "USD"}
    assert _money(booking)["currency"] == "COP"
    assert _money({"price": 0, "commission": 0}) == {}  # cancelada / sin valor
    assert _money({"price": 500000})["currency"] is None  # moneda de la propiedad


async def _unit(session):
    prop = Property(name="Apto", city="Sabaneta", external_ref="p1", currency="COP")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR", external_ref="u1")
    session.add(unit)
    await session.flush()
    return unit


def _bk(unit, ref, ci, co, kind, amount=None, commission=None, currency=None,
        status=BookingStatus.confirmed):
    return Booking(unit_type_id=unit.id, channel_kind=kind, check_in=ci, check_out=co,
                   status=status, external_ref=ref, amount=amount, commission=commission,
                   currency=currency, guest_name="No debe salir")


async def test_meses_reales_estimados_y_contra_arriendo(session):
    unit = await _unit(session)
    session.add_all([
        # Booking.com en pesos: 4 noches en octubre
        _bk(unit, "b1", date(2026, 10, 9), date(2026, 10, 13), ChannelKind.booking,
            D("1120000"), D("172000"), "COP"),
        # Airbnb en dólares, cruza de agosto a septiembre (2 + 1 noches); TRM 4.000
        _bk(unit, "a1", date(2026, 8, 30), date(2026, 9, 2), ChannelKind.airbnb,
            D("300"), D("45"), "USD"),
        FxRate(currency="USD", quote="COP", day=date(2026, 8, 28), rate=D("4000")),
        # Sin valor del canal: precio del calendario y comisión típica (Airbnb 15,5 %)
        _bk(unit, "m1", date(2026, 7, 10), date(2026, 7, 12), ChannelKind.airbnb),
        Rate(unit_type_id=unit.id, date=date(2026, 7, 10), base_price=D("200000")),
        Rate(unit_type_id=unit.id, date=date(2026, 7, 11), base_price=D("200000")),
        # Cancelada: no cuenta
        _bk(unit, "c1", date(2026, 10, 20), date(2026, 10, 25), ChannelKind.booking,
            D("900000"), D("0"), "COP", status=BookingStatus.cancelled),
    ])
    await session.flush()
    await svc.save_settings(session, unit.id, reference_rent=D("2800000"),
                            fixed_costs=D("600000"), cleaning_per_stay=D("80000"))
    rep = await svc.report(session, unit.id, today=TODAY, months_back=4, months_ahead=1)
    by = {m["month"]: m for m in rep["months"]}
    assert list(by) == ["2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"]

    oct_ = by["2026-10"]
    assert (oct_["nights"], oct_["stays"], oct_["gross"], oct_["commission"]) == (4, 1, 1120000, 172000)
    assert oct_["net"] == 1120000 - 172000 - 80000 - 600000 and not oct_["estimated"]

    aug, sep = by["2026-08"], by["2026-09"]
    assert (aug["nights"], sep["nights"]) == (2, 1)
    assert aug["gross"] == 800000 and sep["gross"] == 400000  # 300 USD × 4.000 / 3 noches
    assert aug["commission"] == 120000 and aug["stays"] == 1 and sep["stays"] == 0

    jul = by["2026-07"]
    assert jul["estimated"] and jul["gross"] == 400000 and jul["commission"] == 62000
    assert jul["vs_rent"] == 400000 - 62000 - 80000 - 600000 - 2800000
    assert by["2026-11"]["future"] and by["2026-11"]["nights"] == 0

    s = rep["summary"]  # meses cerrados: jun–sep (octubre está en curso)
    assert s["months"] == 4 and s["estimated"] and s["breakeven_nights"] > 0
    assert "No debe salir" not in str(rep)


async def test_trm_se_guarda_una_vez_y_sin_red_en_el_informe(session):
    unit = await _unit(session)
    session.add(_bk(unit, "a1", date(2026, 9, 4), date(2026, 9, 7), ChannelKind.airbnb,
                    D("385"), D("71.02"), "USD"))
    await session.flush()
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.params["$where"])
        return httpx.Response(200, json=[
            {"valor": "3141.36", "vigenciadesde": "2026-09-04T00:00:00.000",
             "vigenciahasta": "2026-09-04T00:00:00.000"},
            {"valor": "3185.01", "vigenciadesde": "2026-10-23T00:00:00.000",
             "vigenciahasta": "2026-10-23T00:00:00.000"},
        ])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    assert await fx_service.refresh_for_bookings(session, TODAY, client) == 2
    assert await fx_service.refresh_for_bookings(session, TODAY, client) == 0  # ya están
    await client.aclose()
    assert len(calls) == 1
    assert await fx_service.rate_for(session, "USD", date(2026, 9, 6)) == D("3141.36")  # fin de semana
    rows = (await session.execute(select(FxRate))).scalars().all()
    assert len(rows) == 2


async def test_aislamiento_por_cuenta(session, other_session):
    unit = await _unit(session)
    await svc.save_settings(session, unit.id, reference_rent=D("2500000"), fixed_costs=None,
                            cleaning_per_stay=None)
    await session.commit()
    with pytest.raises(LookupError):
        await svc.report(other_session, unit.id, today=TODAY)
    assert await svc.get_settings(other_session, unit.id) is None
