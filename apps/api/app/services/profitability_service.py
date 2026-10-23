"""Rentabilidad mensual de una unidad (feature 042): renta corta frente a un arriendo tradicional.

Por mes:
- noches ocupadas y ocupación;
- ingreso bruto y comisiones de los canales, prorrateados por noche;
- aseo por estancia (en el mes de llegada) y costos fijos;
- neto, y diferencia contra el arriendo de referencia que declara el anfitrión.

Valores reales cuando el channel manager los reporta (Beds24: total y comisión; Airbnb en USD
se pasa a pesos con la TRM del día de llegada). Sin valor (modo sin conexión, reservas viejas)
se **estima** con el precio del calendario y una comisión típica del canal; el mes queda marcado
como estimado. Nunca usa nombres de huéspedes.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.calendar import Rate
from app.models.enums import BookingStatus, ChannelKind
from app.models.finance import UnitFinance
from app.models.property import Property, UnitType
from app.services import fx_service

# Comisión típica cuando el canal no la reporta (Airbnb tarifa solo-anfitrión con software).
DEFAULT_COMMISSION = {ChannelKind.airbnb: Decimal("0.155"), ChannelKind.booking: Decimal("0.15"),
                      ChannelKind.direct: Decimal("0")}
ZERO = Decimal(0)


def _money(v: Decimal) -> int:
    return int(v.quantize(Decimal(1), rounding=ROUND_HALF_UP))


@dataclass
class Month:
    month: str  # YYYY-MM
    days: int
    nights: int = 0
    stays: int = 0
    gross: Decimal = ZERO
    commission: Decimal = ZERO
    estimated: bool = False
    future: bool = False
    by_channel: dict[str, int] = field(default_factory=dict)


def _add_months(d: date, k: int) -> date:
    y, m = divmod(d.month - 1 + k, 12)
    return date(d.year + y, m + 1, 1)


async def get_settings(session: AsyncSession, unit_type_id: int) -> UnitFinance | None:
    return (
        await session.execute(select(UnitFinance).where(UnitFinance.unit_type_id == unit_type_id))
    ).scalar_one_or_none()


async def save_settings(session: AsyncSession, unit_type_id: int, *, reference_rent: Decimal | None,
                        fixed_costs: Decimal | None, cleaning_per_stay: Decimal | None) -> UnitFinance:
    s = await get_settings(session, unit_type_id)
    if s is None:
        s = UnitFinance(unit_type_id=unit_type_id)
        session.add(s)
    s.reference_rent, s.fixed_costs, s.cleaning_per_stay = reference_rent, fixed_costs, cleaning_per_stay
    await session.flush()
    return s


async def report(session: AsyncSession, unit_type_id: int, *, today: date | None = None,
                 months_back: int = 12, months_ahead: int = 3) -> dict:
    today = today or date.today()
    unit = await session.get(UnitType, unit_type_id)
    if unit is None:
        raise LookupError("No existe esa unidad")
    prop = await session.get(Property, unit.property_id)
    local = (prop.currency if prop else None) or "COP"
    units = max(unit.units_count or 1, 1)

    this_month = date(today.year, today.month, 1)
    first = _add_months(this_month, -months_back)
    starts = [_add_months(first, i) for i in range(months_back + 1 + months_ahead)]
    end = _add_months(starts[-1], 1)  # primer día después del último mes
    months = {
        s.strftime("%Y-%m"): Month(month=s.strftime("%Y-%m"),
                                    days=calendar.monthrange(s.year, s.month)[1] * units,
                                    future=s > this_month)
        for s in starts
    }

    bookings = (
        await session.execute(
            select(Booking).where(
                Booking.unit_type_id == unit_type_id, Booking.status == BookingStatus.confirmed,
                Booking.check_out > first, Booking.check_in < end,
            )
        )
    ).scalars().all()
    rates = {
        r.date: r.base_price
        for r in (
            await session.execute(
                select(Rate).where(Rate.unit_type_id == unit_type_id, Rate.date >= first,
                                   Rate.date < end)
            )
        ).scalars()
    }
    missing_fx = False
    for b in bookings:
        nights = (b.check_out - b.check_in).days
        if nights <= 0:
            continue
        per_gross: Decimal | None = None
        per_comm = ZERO
        estimated = False
        if b.amount is not None and b.amount > 0:
            rate = await fx_service.rate_for(session, b.currency or local, b.check_in, local)
            if rate is None:
                rate = await fx_service.latest(session, b.currency or local, local)
                estimated = True
                missing_fx = rate is None or missing_fx
            if rate is not None:
                per_gross = b.amount * rate / nights
                per_comm = (b.commission or ZERO) * rate / nights
        default_pct = DEFAULT_COMMISSION.get(b.channel_kind, ZERO)
        stay_month = b.check_in.strftime("%Y-%m")
        if stay_month in months:
            months[stay_month].stays += 1
        d = b.check_in
        while d < b.check_out:
            key = d.strftime("%Y-%m")
            mo = months.get(key)
            if mo is not None:
                if per_gross is not None:
                    g, c = per_gross, per_comm
                else:  # sin valor del canal: precio del calendario y comisión típica
                    g = rates.get(d, ZERO)
                    c = g * default_pct
                    mo.estimated = True
                mo.estimated = mo.estimated or estimated
                mo.nights += 1
                mo.gross += g
                mo.commission += c
                ch = b.channel_kind.value
                mo.by_channel[ch] = mo.by_channel.get(ch, 0) + 1
            d += timedelta(days=1)

    s = await get_settings(session, unit_type_id)
    rent = s.reference_rent if s and s.reference_rent is not None else None
    fixed = s.fixed_costs if s and s.fixed_costs is not None else ZERO
    cleaning = s.cleaning_per_stay if s and s.cleaning_per_stay is not None else ZERO

    rows = []
    totals = {"nights": 0, "days": 0, "gross": ZERO, "commission": ZERO, "cleaning": ZERO,
              "fixed": ZERO, "net": ZERO, "rent": ZERO}
    for key in sorted(months):
        mo = months[key]
        payout = mo.gross - mo.commission
        clean = cleaning * mo.stays
        net = payout - clean - fixed
        row = {
            "month": key, "future": mo.future, "estimated": mo.estimated,
            "nights": mo.nights, "occupancy": round(100 * mo.nights / mo.days) if mo.days else 0,
            "stays": mo.stays, "gross": _money(mo.gross), "commission": _money(mo.commission),
            "cleaning": _money(clean), "fixed": _money(fixed), "net": _money(net),
            "adr": _money(mo.gross / mo.nights) if mo.nights else None,
            "reference_rent": _money(rent) if rent is not None else None,
            "vs_rent": _money(net - rent) if rent is not None else None,
            "by_channel": mo.by_channel,
        }
        rows.append(row)
        if not mo.future and key != today.strftime("%Y-%m"):
            totals["nights"] += mo.nights
            totals["days"] += mo.days
            totals["gross"] += mo.gross
            totals["commission"] += mo.commission
            totals["cleaning"] += clean
            totals["fixed"] += fixed
            totals["net"] += net
            totals["rent"] += rent or ZERO
    closed = [r for r in rows if not r["future"] and r["month"] != today.strftime("%Y-%m")]
    n_closed = len(closed) or 1
    avg_net_payout_per_night = (
        (totals["gross"] - totals["commission"]) / totals["nights"] if totals["nights"] else None
    )
    # Noches al mes que hacen falta para igualar el arriendo con el neto por noche observado.
    breakeven = None
    if rent is not None and avg_net_payout_per_night and avg_net_payout_per_night > 0:
        stays_per_night = (Decimal(sum(r["stays"] for r in closed)) / totals["nights"]
                           if totals["nights"] else ZERO)
        per_night = avg_net_payout_per_night - cleaning * stays_per_night
        if per_night > 0:
            breakeven = int(((rent + fixed) / per_night).to_integral_value(rounding="ROUND_CEILING"))
    return {
        "currency": local,
        "unit_type_id": unit_type_id,
        "settings": {
            "reference_rent": _money(rent) if rent is not None else None,
            "fixed_costs": _money(fixed) if s and s.fixed_costs is not None else None,
            "cleaning_per_stay": _money(cleaning) if s and s.cleaning_per_stay is not None else None,
        },
        "months": rows,
        "summary": {
            "months": len(closed),
            "occupancy": round(100 * totals["nights"] / totals["days"]) if totals["days"] else 0,
            "gross": _money(totals["gross"]),
            "net": _money(totals["net"]),
            "net_monthly_avg": _money(totals["net"] / n_closed),
            "rent_monthly": _money(rent) if rent is not None else None,
            "vs_rent_total": _money(totals["net"] - totals["rent"]) if rent is not None else None,
            "breakeven_nights": breakeven,
            "estimated": any(r["estimated"] for r in closed),
            "missing_fx": missing_fx,
        },
    }
