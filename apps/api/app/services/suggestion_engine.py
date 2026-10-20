"""Motor de sugerencias v2 (feature 018): agrupación por rango, supersede, explicable.

Una sugerencia cubre el RANGO de un evento o los días contiguos con la misma señal
y el mismo precio base (se corta si el base cambia). Las noches ocupadas (reserva o
bloqueo) se excluyen. Al persistir un rango nuevo, las pendientes solapadas quedan
`superseded` (nunca dos pendientes para la misma noche); las vencidas se depuran al
inicio de cada corrida y, al final, las pendientes del horizonte que el scan ya no
respalda (p. ej. la noche se reservó o la señal desapareció) también.

No repetición: el cálculo parte del precio que fijó el host (sin la subida de una
sugerencia ya aplicada) y una noche ya decidida (aplicada o rechazada) solo vuelve a
proponerse ante un cambio drástico; en ese caso el racional lleva `previous` con la
decisión anterior (ver app/domain/suggestion_repeat.py).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain import municipalities
from app.domain import suggestion_repeat as repeat
from app.domain.suggestion import EventSignal, suggest_price_v2
from app.market.provider import MarketDataProvider, MarketSnapshot
from app.models.audit import PriceChangeLog
from app.models.calendar import CalendarDay
from app.models.enums import ChangeOrigin, EventKind, Relevance, SuggestionStatus
from app.models.market import Event, PriceSuggestion
from app.models.property import Property, UnitType
from app.services import pricing_service

_REL_ORDER = {Relevance.low: 0, Relevance.medium: 1, Relevance.high: 2}
_OCC_WINDOW = 7  # ±días para la señal de ocupación de la zona propia
_GAP_WINDOW = 14  # ventana de hueco próximo (host, clarify)
# Feature 039: ocupación de los próximos días por debajo de esto = demanda baja.
LOW_DEMAND_WINDOW = 30
LOW_DEMAND_OCC = 0.30


# --------- supersede (US5) ---------


async def _supersede_expired(session: AsyncSession, unit_type_id: int, today: date) -> int:
    res = await session.execute(
        update(PriceSuggestion)
        .where(
            PriceSuggestion.unit_type_id == unit_type_id,
            PriceSuggestion.status == SuggestionStatus.proposed,
            PriceSuggestion.date_to < today,
        )
        .values(status=SuggestionStatus.superseded)
    )
    await session.flush()
    return res.rowcount or 0


async def _supersede_overlapping(
    session: AsyncSession, unit_type_id: int, date_from: date, date_to: date
) -> int:
    res = await session.execute(
        update(PriceSuggestion)
        .where(
            PriceSuggestion.unit_type_id == unit_type_id,
            PriceSuggestion.status == SuggestionStatus.proposed,
            PriceSuggestion.date_from <= date_to,
            PriceSuggestion.date_to >= date_from,
        )
        .values(status=SuggestionStatus.superseded)
    )
    await session.flush()
    return res.rowcount or 0


async def _supersede_not_regenerated(
    session: AsyncSession, unit_type_id: int, date_from: date, date_to: date, keep: set[int]
) -> int:
    """Pendientes del horizonte que este scan ya no respalda (señal desaparecida, noche
    ocupada, motor anterior…) → `superseded`. Las resueltas no se tocan."""
    stmt = (
        update(PriceSuggestion)
        .where(
            PriceSuggestion.unit_type_id == unit_type_id,
            PriceSuggestion.status == SuggestionStatus.proposed,
            PriceSuggestion.date_from <= date_to,
            PriceSuggestion.date_to >= date_from,
        )
        .values(status=SuggestionStatus.superseded)
    )
    if keep:
        stmt = stmt.where(PriceSuggestion.id.not_in(keep))
    res = await session.execute(stmt)
    await session.flush()
    return res.rowcount or 0


async def _exists_equivalent(
    session: AsyncSession, unit_type_id: int, date_from: date, date_to: date, price: Decimal
) -> PriceSuggestion | None:
    """Sugerencia equivalente (mismo rango y precio) en cualquier estado no
    reemplazado, o None. Evita re-proponer lo ya pendiente/aplicado/rechazado."""
    res = await session.execute(
        select(PriceSuggestion).where(
            PriceSuggestion.unit_type_id == unit_type_id,
            PriceSuggestion.date_from == date_from,
            PriceSuggestion.date_to == date_to,
            PriceSuggestion.suggested_price == price,
            PriceSuggestion.status.in_(
                (
                    SuggestionStatus.proposed,
                    SuggestionStatus.approved,
                    SuggestionStatus.applied,
                    SuggestionStatus.rejected,
                )
            ),
        )
    )
    found = list(res.scalars())
    # Preferir la pendiente: es la que se conserva y refresca (019 · US4).
    pending = [s for s in found if s.status in (SuggestionStatus.proposed, SuggestionStatus.approved)]
    return (pending or found or [None])[0]


# --------- no repetición: decisiones previas y precio de referencia ---------


async def _prior_decisions(
    session: AsyncSession, unit_type_id: int, date_from: date, date_to: date
) -> dict[date, repeat.PriorDecision]:
    """Última decisión del host (aplicada o rechazada) por noche del horizonte.

    Nunca hay dos pendientes para la misma noche (supersede), así que el id más alto
    es la decisión más reciente.
    """
    res = await session.execute(
        select(PriceSuggestion)
        .where(
            PriceSuggestion.unit_type_id == unit_type_id,
            PriceSuggestion.status.in_((SuggestionStatus.applied, SuggestionStatus.rejected)),
            PriceSuggestion.date_from <= date_to,
            PriceSuggestion.date_to >= date_from,
        )
        .order_by(PriceSuggestion.id)
    )
    out: dict[date, repeat.PriorDecision] = {}
    for s in res.scalars():
        decision = repeat.PriorDecision(
            suggestion_id=s.id,
            status=s.status.value,
            price=s.suggested_price,
            date_from=s.date_from,
            date_to=s.date_to,
            decided_on=s.updated_at.date() if s.updated_at else None,
        )
        day = max(s.date_from, date_from)
        while day <= min(s.date_to, date_to):
            out[day] = decision  # la más reciente gana
            day += timedelta(days=1)
    return out


async def _price_logs(
    session: AsyncSession, unit_type_id: int, date_from: date, date_to: date
) -> dict[date, list[repeat.PriceLog]]:
    """Bitácora de precios del horizonte por noche, del cambio más nuevo al más viejo."""
    res = await session.execute(
        select(PriceChangeLog)
        .where(
            PriceChangeLog.unit_type_id == unit_type_id,
            PriceChangeLog.date >= date_from,
            PriceChangeLog.date <= date_to,
        )
        .order_by(PriceChangeLog.id.desc())
    )
    out: dict[date, list[repeat.PriceLog]] = {}
    for log in res.scalars():
        out.setdefault(log.date, []).append(
            repeat.PriceLog(
                old_price=log.old_price,
                new_price=log.new_price,
                from_suggestion=log.origin is ChangeOrigin.suggestion,
            )
        )
    return out


# --------- señales por día ---------


def _event_for(events: list[Event], day: date) -> Event | None:
    best: Event | None = None
    for ev in events:
        end = ev.end_date or ev.start_date
        if ev.start_date <= day <= end:
            if best is None or _REL_ORDER[ev.relevance] > _REL_ORDER[best.relevance]:
                best = ev
    return best


def _cap_for(cap, ev: Event | None, low_demand: bool):
    """Feature 039: con demanda baja, solo los eventos grandes y los festivos/puentes pueden
    acercarse al p90; los medianos, pequeños o sin evento topan en el p75."""
    from dataclasses import replace

    if cap is None or not low_demand or cap.p75 is None:
        return cap
    if ev is not None and (ev.relevance == Relevance.high or ev.kind == EventKind.holiday):
        return cap
    return replace(cap, p90=cap.p75, level="p75")


def _occupancy_high(occupied: set[date], day: date) -> bool:
    """Demanda propia alta: ≥50% de los días de la ventana ±7 ya están tomados."""
    window = [day + timedelta(days=i) for i in range(-_OCC_WINDOW, _OCC_WINDOW + 1)]
    taken = sum(1 for d in window if d in occupied)
    return taken / len(window) >= 0.5


def _event_signal(ev: Event) -> EventSignal:
    dates = ev.start_date.isoformat()
    if ev.end_date and ev.end_date != ev.start_date:
        dates += f" → {ev.end_date.isoformat()}"
    return EventSignal(
        relevance=ev.relevance,
        name=ev.name,
        location=ev.location,
        dates=dates,
        source_url=ev.source_url,
    )


def _rationale(
    out, market: MarketSnapshot | None, previous: repeat.PriorDecision | None = None
) -> dict:
    data: dict = {
        "text": out.text,
        "factors": [
            {
                "kind": f.kind,
                "label": f.label,
                "pct": float(f.pct) if f.pct is not None else None,
                **({"event": f.event} if f.event else {}),
                **(f.data or {}),
            }
            for f in out.factors
        ],
    }
    if market is not None and market.adr is not None:
        data["market"] = {
            "adr": str(market.adr),
            "samples": market.sample_size,
            "source": market.source,
        }
    if previous is not None:
        # Re-propuesta por cambio drástico: la web avisa qué se había decidido antes.
        data["previous"] = previous.as_dict(Decimal(str(settings.suggestion_repeat_threshold_pct)))
    return data


# --------- generación ---------


async def generate_suggestions(
    session: AsyncSession,
    *,
    unit_type_id: int,
    date_from: date,
    date_to: date,
    market: MarketDataProvider | None = None,
    today: date | None = None,
) -> list[PriceSuggestion]:
    unit = await session.get(UnitType, unit_type_id)
    prop = await session.get(Property, unit.property_id)
    today = today or date.today()
    rule = await pricing_service.get_active_rule(session, prop.id)
    min_p = rule.min_price if rule else None
    max_p = rule.max_price if rule else None

    await _supersede_expired(session, unit_type_id, today)

    events = list(
        (
            await session.execute(
                select(Event).where(
                    Event.start_date <= date_to,
                    # Municipio + ciudad principal del área (Sabaneta → Medellín), feature 033.
                    Event.city.in_(municipalities.area_keys(prop.city)),
                )
            )
        ).scalars()
    )
    occupied = {
        row[0]
        for row in (
            await session.execute(
                select(CalendarDay.date).where(
                    CalendarDay.unit_type_id == unit_type_id,
                    CalendarDay.units_available == 0,
                )
            )
        ).all()
    }

    # Snapshot de mercado por mes (una consulta por mes del horizonte).
    zone = ", ".join(p for p in (prop.city, prop.address) if p)
    snapshots: dict[tuple[int, int], MarketSnapshot | None] = {}
    if market is not None:
        month = date(date_from.year, date_from.month, 1)
        while month <= date_to:
            snapshots[(month.year, month.month)] = await market.get_snapshot(zone, month)
            month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)

    horizon_from = max(date_from, today)
    # Feature 038: techo de mercado (p90 de la zona y su tamaño) por noche, si hay datos.
    from app.services import market_band_service

    caps = await market_band_service.caps_for(
        session, prop.city, market_band_service.unit_bedrooms(unit), horizon_from, date_to
    )
    window = [today + timedelta(days=i) for i in range(LOW_DEMAND_WINDOW)]
    low_demand = sum(1 for d in window if d in occupied) / LOW_DEMAND_WINDOW < LOW_DEMAND_OCC
    decisions = await _prior_decisions(session, unit_type_id, horizon_from, date_to)
    logs = await _price_logs(session, unit_type_id, horizon_from, date_to)
    threshold = Decimal(str(settings.suggestion_repeat_threshold_pct))
    tolerance = Decimal(str(settings.suggestion_same_price_tolerance_pct))

    # Cálculo por día (solo días con precio, libres y no pasados) y agrupación
    # por (clave de señal, precio sugerido, decisión previa): días contiguos → un rango.
    per_day: list[tuple[date, tuple, object, MarketSnapshot | None, repeat.PriorDecision | None]] = []
    day = horizon_from
    while day <= date_to:
        current = await pricing_service.get_price(session, unit_type_id, day)
        if current is None or day in occupied:
            day += timedelta(days=1)
            continue
        # El motor calcula sobre el precio del host, no sobre una subida ya aplicada.
        base = repeat.reference_base(current, logs.get(day, []))
        ev = _event_for(events, day)
        occ = _occupancy_high(occupied, day)
        gap = (day - today).days if ev is None and not occ and (day - today).days <= _GAP_WINDOW else None
        snap = snapshots.get((day.year, day.month))
        out = suggest_price_v2(
            base,
            event=_event_signal(ev) if ev else None,
            occupancy_high=occ,
            gap_days_ahead=gap,
            market=snap,
            min_price=min_p,
            max_price=max_p,
            market_cap=_cap_for(caps.get(day), ev, low_demand),
        )
        prior = decisions.get(day)
        if out is not None and repeat.should_propose(
            out.price,
            current=current,
            reference=base,
            prior_price=prior.price if prior else None,
            threshold_pct=threshold,
            tolerance_pct=tolerance,
        ):
            # Clave de agrupación: misma señal dominante, mismo precio y misma decisión previa.
            capped = any(f.kind == "market_cap" for f in out.factors)
            key = (ev.id if ev else None, occ, gap is not None, capped, out.price, prior)
            per_day.append((day, key, out, snap, prior))
        day += timedelta(days=1)

    created: list[PriceSuggestion] = []
    keep: set[int] = set()
    i = 0
    while i < len(per_day):
        start_day, key, out, snap, prior = per_day[i]
        j = i
        while (
            j + 1 < len(per_day)
            and per_day[j + 1][1] == key
            and per_day[j + 1][0] == per_day[j][0] + timedelta(days=1)
        ):
            j += 1
        end_day = per_day[j][0]

        equivalent = await _exists_equivalent(session, unit_type_id, start_day, end_day, out.price)
        if equivalent is not None:
            keep.add(equivalent.id)
            if equivalent.status in (SuggestionStatus.proposed, SuggestionStatus.approved):
                # Misma identidad y estado, explicación del último scan (019 · US4).
                equivalent.rationale = _rationale(out, snap, prior)
                equivalent.confidence = out.confidence
        else:
            await _supersede_overlapping(session, unit_type_id, start_day, end_day)
            sug = PriceSuggestion(
                property_id=prop.id,
                unit_type_id=unit_type_id,
                date_from=start_day,
                date_to=end_day,
                suggested_price=out.price,
                rationale=_rationale(out, snap, prior),
                confidence=out.confidence,
                status=SuggestionStatus.proposed,
            )
            session.add(sug)
            created.append(sug)
        i = j + 1

    await session.flush()
    keep.update(s.id for s in created)
    await _supersede_not_regenerated(session, unit_type_id, horizon_from, date_to, keep)
    return created
