"""Extensión de precios hacia el futuro (feature 023).

Vista previa: lee el calendario REAL del Channel Manager (la app solo sincroniza
365 días) y clasifica cada noche: con precio → no se toca; reservada → se omite;
sin precio → recibe el precio de la plantilla y, si está cerrada y el host no la
bloqueó desde la app, se abre. Aplicación por mes en SAVEPOINT: auditoría local
(origen `extension`) + una escritura de calendario; si el mes falla, se deshace.
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import CalendarEntry, ChannelManager
from app.channels.errors import ChannelError
from app.domain.price_extension import (
    Clipped,
    add_months,
    is_weekend,
    month_key,
    night_price,
    propose_template,
)
from app.models.audit import PriceChangeLog
from app.models.availability import AvailabilityChangeLog
from app.models.calendar import CalendarDay, Rate
from app.models.enums import ChangeOrigin, Relevance, SyncIssueKind
from app.models.market import Event
from app.models.property import UnitType
from app.models.sync import SyncIssue
from app.services import availability_service, pricing_service

DEFAULT_MONTHS = 18
MAX_MONTHS = 24
WARN_DAYS = 365
MAX_WEEKEND_PCT = Decimal(50)


class ExtensionError(ValueError):
    """Parámetros inválidos (→ 422)."""


@dataclass
class MonthInput:
    month: str
    price: Decimal | None = None
    included: bool = True


@dataclass
class ExtensionParams:
    unit_type_id: int
    until: date | None = None
    weekend_pct: Decimal = Decimal(0)
    open_closed: bool = True
    months: list[MonthInput] | None = None


@dataclass
class ExtensionNight:
    date: date
    price: Decimal
    clipped: Clipped
    open: bool
    kept_closed: bool


@dataclass
class ExtensionMonth:
    month: str
    proposed_price: Decimal | None
    price: Decimal | None
    included: bool
    nights: int = 0
    weekend_nights: int = 0
    weekday_price: Decimal | None = None
    weekend_price: Decimal | None = None
    to_open: int = 0
    kept_closed: int = 0
    clipped_min: int = 0
    clipped_max: int = 0
    items: list[ExtensionNight] = field(default_factory=list)


@dataclass
class ExtensionPreview:
    until: date
    first_target: date | None
    min_price: Decimal | None
    max_price: Decimal | None
    weekend_pct: Decimal
    open_closed: bool
    months: list[ExtensionMonth]
    total_nights: int
    total_to_open: int
    fingerprint: str
    # Noches que YA tienen precio pero están cerradas en el CM (no reservables);
    # la extensión no las toca: se avisan para que el host lo sepa.
    closed_priced: int = 0
    first_closed_priced: date | None = None


@dataclass
class MonthResult:
    month: str
    status: str  # applied | failed | skipped
    nights: int
    opened: int
    detail: str | None = None
    not_opened: int = 0  # se pidió abrir pero el CM las dejó cerradas


@dataclass
class ExtensionResult:
    stale: bool = False
    months: list[MonthResult] = field(default_factory=list)
    applied_nights: int = 0
    opened_nights: int = 0
    failed_months: int = 0
    not_opened_nights: int = 0


@dataclass
class HorizonStatus:
    first_unpriced_night: date | None
    months_covered: int
    needs_extension: bool
    default_until: date
    max_until: date
    # Noches con precio pero cerradas (no reservadas ni bloqueadas por el host desde
    # la app) en los próximos 365 días: con precio y aun así no se pueden reservar.
    closed_nights: int = 0
    first_closed_night: date | None = None


class _MonthNotPublished(Exception):
    """Señal interna: el canal no confirmó la escritura del mes."""


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


async def _known_prices(session: AsyncSession, unit_type_id: int) -> dict[date, Decimal]:
    rows = await session.execute(
        select(Rate.date, Rate.base_price).where(
            Rate.unit_type_id == unit_type_id, Rate.base_price > 0
        )
    )
    return {d: Decimal(p) for d, p in rows}


async def _event_days(session: AsyncSession) -> set[date]:
    """Noches con evento de relevancia ALTA (los de relevancia media/baja cubren casi
    todo el calendario y dejarían la plantilla sin datos)."""
    out: set[date] = set()
    for ev in (
        await session.execute(select(Event).where(Event.relevance == Relevance.high))
    ).scalars():
        out.update(_days(ev.start_date, ev.end_date or ev.start_date))
    return out


async def _blocked_days(session: AsyncSession, unit_type_id: int, first: date, last: date) -> set[date]:
    rows = await session.execute(
        select(CalendarDay.date).where(
            CalendarDay.unit_type_id == unit_type_id,
            CalendarDay.date >= first,
            CalendarDay.date <= last,
            CalendarDay.is_blocked.is_(True),
        )
    )
    return set(rows.scalars())


def _validate(params: ExtensionParams, today: date) -> date:
    until = params.until or add_months(today, DEFAULT_MONTHS)
    if until < today:
        raise ExtensionError("la fecha final no puede ser anterior a hoy")
    if until > add_months(today, MAX_MONTHS):
        raise ExtensionError(f"la fecha final no puede superar {MAX_MONTHS} meses desde hoy")
    if not (Decimal(0) <= params.weekend_pct <= MAX_WEEKEND_PCT):
        raise ExtensionError("el % de fin de semana debe estar entre 0 y 50")
    for m in params.months or []:
        if m.price is not None and m.price <= 0:
            raise ExtensionError(f"el precio de {m.month} debe ser mayor que 0")
    return until


async def preview(
    session: AsyncSession, channel: ChannelManager, params: ExtensionParams, *, today: date
) -> ExtensionPreview:
    until = _validate(params, today)
    unit = await session.get(UnitType, params.unit_type_id)
    if unit is None or not unit.external_ref:
        raise ExtensionError("unidad no encontrada o sin mapear al Channel Manager")
    rule = await pricing_service.get_active_rule(session, unit.property_id)
    min_price = rule.min_price if rule else None
    max_price = rule.max_price if rule else None

    # Estado real del CM (una lectura). Día ausente = sin precio y cerrado.
    remote = {
        r.date: (r.price, r.available)
        for r in await channel.get_rates(unit.external_ref, today, until)
    }
    days = _days(today, until)
    booked = await availability_service._booked_nights(session, unit.id, days)
    blocked = await _blocked_days(session, unit.id, today, until)

    targets = [d for d in days if remote.get(d, (Decimal(0), 0))[0] <= 0 and d not in booked]
    closed_priced = [
        d
        for d in days
        if remote.get(d, (Decimal(0), 0))[0] > 0
        and remote[d][1] <= 0
        and d not in booked
        and d not in blocked
    ]
    month_keys = list(dict.fromkeys(month_key(d) for d in targets))

    known = await _known_prices(session, unit.id)
    for d, (p, _) in remote.items():
        if p > 0:
            known.setdefault(d, p)
    proposed = propose_template(known, await _event_days(session), month_keys, fallback=min_price)
    overrides = {m.month: m for m in params.months or []}

    months: dict[str, ExtensionMonth] = {}
    for key in month_keys:
        ov = overrides.get(key)
        price = ov.price if ov and ov.price is not None else proposed[key]
        included = ov.included if ov else True
        if included and price is None:
            raise ExtensionError(f"falta el precio de {key}")
        months[key] = ExtensionMonth(
            month=key, proposed_price=proposed[key], price=price, included=included
        )

    raw = [
        f"{until}|{params.weekend_pct}|{params.open_closed}|{min_price}|{max_price}",
        *(f"{m.month}={m.price}:{int(m.included)}" for m in months.values()),
    ]
    for d in targets:
        m = months[month_key(d)]
        r_price, r_avail = remote.get(d, (Decimal(0), 0))
        raw.append(f"{d.isoformat()}:{r_price}:{r_avail}:{int(d in blocked)}")
        m.nights += 1
        weekend = is_weekend(d)
        m.weekend_nights += int(weekend)
        if m.price is None:
            continue
        price, clipped = night_price(m.price, d, params.weekend_pct, min_price, max_price)
        if weekend and m.weekend_price is None:
            m.weekend_price = price
        if not weekend and m.weekday_price is None:
            m.weekday_price = price
        do_open = params.open_closed and r_avail <= 0 and d not in blocked
        kept_closed = r_avail <= 0 and not do_open
        m.to_open += int(do_open)
        m.kept_closed += int(kept_closed)
        m.clipped_min += int(clipped == "min")
        m.clipped_max += int(clipped == "max")
        m.items.append(ExtensionNight(d, price, clipped, do_open, kept_closed))

    included = [m for m in months.values() if m.included]
    return ExtensionPreview(
        until=until,
        first_target=targets[0] if targets else None,
        min_price=min_price,
        max_price=max_price,
        weekend_pct=params.weekend_pct,
        open_closed=params.open_closed,
        months=list(months.values()),
        total_nights=sum(m.nights for m in included),
        total_to_open=sum(m.to_open for m in included),
        fingerprint=hashlib.sha256(";".join(raw).encode()).hexdigest()[:16],
        closed_priced=len(closed_priced),
        first_closed_priced=closed_priced[0] if closed_priced else None,
    )


def _entries(items: list[ExtensionNight], num_avail: int) -> list[CalendarEntry]:
    """Noches contiguas con igual (precio, abrir) → un tramo."""
    groups: list[list] = []
    for n in sorted(items, key=lambda x: x.date):
        if (
            groups
            and groups[-1][1] + timedelta(days=1) == n.date
            and groups[-1][2] == n.price
            and groups[-1][3] == n.open
        ):
            groups[-1][1] = n.date
        else:
            groups.append([n.date, n.date, n.price, n.open])
    return [CalendarEntry(a, b, p, num_avail if o else None) for a, b, p, o in groups]


async def _write_month_locally(
    session: AsyncSession, unit: UnitType, items: list[ExtensionNight], target_avail: int
) -> dict[date, tuple[CalendarDay, AvailabilityChangeLog]]:
    """Precios + auditoría + aperturas del mes en lote (pocas consultas, un solo flush).

    Noche a noche costaba ~0,5 s por noche contra la BD remota; con 15 meses la
    petición superaba el tiempo del proxy y se cortaba a mitad (2026-10-09).
    """
    days = [n.date for n in items]
    rates = {
        r.date: r
        for r in (
            await session.execute(
                select(Rate).where(Rate.unit_type_id == unit.id, Rate.date.in_(days))
            )
        ).scalars()
    }
    open_days = [n.date for n in items if n.open]
    cds = (
        {
            c.date: c
            for c in (
                await session.execute(
                    select(CalendarDay).where(
                        CalendarDay.unit_type_id == unit.id, CalendarDay.date.in_(open_days)
                    )
                )
            ).scalars()
        }
        if open_days
        else {}
    )
    opened: dict[date, tuple[CalendarDay, AvailabilityChangeLog]] = {}
    for n in items:
        rate = rates.get(n.date)
        old = rate.base_price if rate is not None and rate.base_price > 0 else None
        if rate is None:
            session.add(Rate(unit_type_id=unit.id, date=n.date, base_price=n.price))
        else:
            rate.base_price = n.price
        session.add(
            PriceChangeLog(
                unit_type_id=unit.id,
                date=n.date,
                old_price=old,
                new_price=n.price,
                origin=ChangeOrigin.extension,
            )
        )
        if n.open:
            cd = cds.get(n.date)
            if cd is None:
                cd = CalendarDay(unit_type_id=unit.id, date=n.date, units_available=0)
                session.add(cd)
            log = AvailabilityChangeLog(
                unit_type_id=unit.id,
                date=n.date,
                old_units_available=cd.units_available,
                new_units_available=target_avail,
                was_blocked=bool(cd.is_blocked),
                is_blocked=False,
                origin=ChangeOrigin.extension,
            )
            session.add(log)
            cd.units_available = target_avail
            cd.is_blocked = False
            opened[n.date] = (cd, log)
    await session.flush()
    return opened


async def apply(
    session: AsyncSession,
    channel: ChannelManager,
    params: ExtensionParams,
    fingerprint: str,
    *,
    today: date,
    on_month_done: Callable[[], Awaitable[None]] | None = None,
) -> ExtensionResult:
    """Aplica mes a mes. `on_month_done` (la ruta pasa `session.commit`) persiste cada
    mes apenas el CM lo confirma: un corte posterior no deshace lo ya publicado."""
    prev = await preview(session, channel, params, today=today)
    if prev.fingerprint != fingerprint:
        return ExtensionResult(stale=True)

    unit = await session.get(UnitType, params.unit_type_id)
    target_avail = unit.units_count or 1
    result = ExtensionResult()
    for m in prev.months:
        if not m.included or not m.items:
            result.months.append(MonthResult(m.month, "skipped", m.nights, 0))
            continue
        failure: str | None = None
        warning: str | None = None
        not_opened = 0
        try:
            async with session.begin_nested():
                opened_local = await _write_month_locally(session, unit, m.items, target_avail)
                res = await channel.set_calendar_entries(
                    unit.external_ref, _entries(m.items, target_avail)
                )
                if not (res.ok and res.verified):
                    raise _MonthNotPublished(res.detail or "escritura no verificada")
                warning = res.detail  # precio confirmado; aviso p. ej. disponibilidad
                if res.unconfirmed and opened_local:
                    # La app refleja lo que REALMENTE quedó en el CM (no lo pedido).
                    first, last = min(opened_local), max(opened_local)
                    real = {
                        r.date: r.available
                        for r in await channel.get_rates(unit.external_ref, first, last)
                    }
                    for d, (cd, log) in opened_local.items():
                        avail = real.get(d, 0)
                        if avail < target_avail:
                            not_opened += 1
                            cd.units_available = avail
                            log.new_units_available = avail
                    await session.flush()
        except _MonthNotPublished as exc:
            failure = str(exc)
        except ChannelError as exc:
            failure = f"error al publicar ({exc})"
        if failure:
            session.add(
                SyncIssue(
                    kind=SyncIssueKind.comm_error,
                    entity_ref=f"price-extension:{m.month}",
                    detail=failure,
                )
            )
            await session.flush()
            result.failed_months += 1
            result.months.append(MonthResult(m.month, "failed", len(m.items), 0, failure))
        else:
            if warning:
                session.add(
                    SyncIssue(
                        kind=SyncIssueKind.write_unverified,
                        entity_ref=f"price-extension:{m.month}",
                        detail=warning,
                    )
                )
                await session.flush()
            opened = sum(1 for n in m.items if n.open) - not_opened
            result.applied_nights += len(m.items)
            result.opened_nights += opened
            result.not_opened_nights += not_opened
            result.months.append(
                MonthResult(m.month, "applied", len(m.items), opened, warning, not_opened)
            )
        if on_month_done is not None:
            await on_month_done()
    return result


async def status(session: AsyncSession, unit_type_id: int, *, today: date) -> HorizonStatus:
    """Primera noche futura sin precio (datos locales; la sync diaria cubre 365 días)."""
    limit = add_months(today, MAX_MONTHS)
    priced = set(
        (
            await session.execute(
                select(Rate.date).where(
                    Rate.unit_type_id == unit_type_id,
                    Rate.date >= today,
                    Rate.date <= limit,
                    Rate.base_price > 0,
                )
            )
        ).scalars()
    )
    # Una noche reservada no es un hueco aunque no tenga precio cargado.
    booked = await availability_service._booked_nights(session, unit_type_id, _days(today, limit))
    first: date | None = None
    for d in _days(today, limit):
        if d not in priced and d not in booked:
            first = d
            break
    if first is None:
        covered = MAX_MONTHS
    else:
        covered = (first.year - today.year) * 12 + first.month - today.month
        if first.day < today.day:
            covered -= 1
        covered = max(covered, 0)
    window_end = today + timedelta(days=WARN_DAYS)
    closed_rows = (
        await session.execute(
            select(CalendarDay.date).where(
                CalendarDay.unit_type_id == unit_type_id,
                CalendarDay.date >= today,
                CalendarDay.date <= window_end,
                CalendarDay.units_available <= 0,
                CalendarDay.is_blocked.is_(False),
            )
        )
    ).scalars()
    closed = sorted(d for d in closed_rows if d in priced and d not in booked)
    return HorizonStatus(
        closed_nights=len(closed),
        first_closed_night=closed[0] if closed else None,
        first_unpriced_night=first,
        months_covered=covered,
        needs_extension=first is not None and first < today + timedelta(days=WARN_DAYS),
        default_until=add_months(today, DEFAULT_MONTHS),
        max_until=limit,
    )
