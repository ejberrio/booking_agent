"""Sugerencias accionables (feature 019): noches vendibles, bloques y aplicación en lote.

- **Vendible** = noche futura sin reserva confirmada, sin bloqueo y sin inventario 0.
  Se calcula al consultar (nada se almacena): una cancelación sincronizada hace
  reaparecer la sugerencia sin esperar al scan.
- **Lote**: una vista previa (noche a noche, con omisiones y huella) y una confirmación.
  El apply recalcula la vista previa (huella distinta → stale, sin escribir) y aplica
  por tramos contiguos de igual precio dentro de un SAVEPOINT: si la publicación de un
  tramo falla (incidencias o excepción), ese tramo se revierte localmente y sus
  sugerencias siguen pendientes. Nunca queda `applied` algo que no llegó al canal.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.pricing import violates_rule
from app.models.audit import PriceChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay
from app.models.enums import BookingStatus, ChangeOrigin, SuggestionStatus, SyncIssueKind
from app.models.market import PriceSuggestion
from app.models.property import UnitType
from app.models.sync import SyncIssue
from app.services import pricing_app_service, pricing_service

_PENDING = (SuggestionStatus.proposed, SuggestionStatus.approved)


class _TramoNoPublicado(Exception):
    """Señal interna: el canal reportó incidencias para el tramo."""


@dataclass(frozen=True)
class SellableNight:
    date: date
    suggestion_id: int
    current_price: Decimal | None
    suggested_price: Decimal


@dataclass
class SuggestionView:
    suggestion: PriceSuggestion
    nights: list[SellableNight] = field(default_factory=list)
    occupied_count: int = 0
    total_nights: int = 0


@dataclass(frozen=True)
class BatchPreviewItem:
    date: date
    suggestion_id: int
    old_price: Decimal | None
    new_price: Decimal
    valid: bool
    reason: str | None = None


@dataclass
class BatchPreview:
    suggestion_ids: list[int]
    items: list[BatchPreviewItem]
    fingerprint: str
    valid_count: int
    skipped_count: int


@dataclass(frozen=True)
class BatchResultNight:
    date: date
    suggestion_id: int
    status: str  # applied | skipped | failed
    reason: str | None = None


@dataclass
class BatchResult:
    nights: list[BatchResultNight] = field(default_factory=list)
    suggestions: dict[int, str] = field(default_factory=dict)  # applied|pending|unchanged
    stale: bool = False

    @property
    def applied_count(self) -> int:
        return sum(1 for n in self.nights if n.status == "applied")

    @property
    def skipped_count(self) -> int:
        return sum(1 for n in self.nights if n.status == "skipped")

    @property
    def failed_count(self) -> int:
        return sum(1 for n in self.nights if n.status == "failed")


def _days(date_from: date, date_to: date) -> list[date]:
    return [date_from + timedelta(days=i) for i in range((date_to - date_from).days + 1)]


# --------- ocupación ---------


async def occupied_nights(
    session: AsyncSession, unit_type_id: int, date_from: date, date_to: date
) -> dict[date, str]:
    """Noches no vendibles del rango con su motivo ("reservada" | "bloqueada").

    El día de salida no ocupa (noches [check_in, check_out)).
    """
    out: dict[date, str] = {}
    bookings = await session.execute(
        select(Booking.check_in, Booking.check_out).where(
            Booking.unit_type_id == unit_type_id,
            Booking.status == BookingStatus.confirmed,
            Booking.check_in <= date_to,
            Booking.check_out > date_from,
        )
    )
    for check_in, check_out in bookings.all():
        d = max(check_in, date_from)
        while d < check_out and d <= date_to:
            out[d] = "reservada"
            d += timedelta(days=1)

    cal = await session.execute(
        select(CalendarDay.date, CalendarDay.units_available, CalendarDay.is_blocked).where(
            CalendarDay.unit_type_id == unit_type_id,
            CalendarDay.date >= date_from,
            CalendarDay.date <= date_to,
        )
    )
    for day, available, blocked in cal.all():
        if blocked:
            out.setdefault(day, "bloqueada")
        elif available == 0:
            out.setdefault(day, "reservada")  # respaldo: reserva del canal no importada
    return out


async def _load(
    session: AsyncSession, ids: list[int] | None, unit_type_id: int | None
) -> list[PriceSuggestion]:
    stmt = select(PriceSuggestion).order_by(PriceSuggestion.date_from, PriceSuggestion.id)
    if ids is not None:
        stmt = stmt.where(PriceSuggestion.id.in_(ids))
    else:
        stmt = stmt.where(PriceSuggestion.status.in_(_PENDING))
    if unit_type_id is not None:
        stmt = stmt.where(PriceSuggestion.unit_type_id == unit_type_id)
    return list((await session.execute(stmt)).scalars())


async def _occupancy_for(
    session: AsyncSession, sugs: list[PriceSuggestion], today: date
) -> dict[int, dict[date, str]]:
    """Ocupación por unidad, en UNA pasada por unidad sobre el rango total."""
    by_unit: dict[int, list[PriceSuggestion]] = {}
    for s in sugs:
        if s.unit_type_id is not None:
            by_unit.setdefault(s.unit_type_id, []).append(s)
    occ: dict[int, dict[date, str]] = {}
    for unit_id, items in by_unit.items():
        lo = max(today, min(s.date_from for s in items))
        hi = max(s.date_to for s in items)
        occ[unit_id] = await occupied_nights(session, unit_id, lo, hi) if lo <= hi else {}
    return occ


async def pending_views(
    session: AsyncSession, *, unit_type_id: int | None = None, today: date | None = None
) -> list[SuggestionView]:
    """Pendientes vigentes reducidas a sus noches vendibles (orden por fecha)."""
    today = today or date.today()
    sugs = [s for s in await _load(session, None, unit_type_id) if s.date_to >= today]
    occ = await _occupancy_for(session, sugs, today)
    views: list[SuggestionView] = []
    for s in sugs:
        if s.unit_type_id is None:
            continue
        future = [d for d in _days(s.date_from, s.date_to) if d >= today]
        busy = occ.get(s.unit_type_id, {})
        nights = [
            SellableNight(
                date=d,
                suggestion_id=s.id,
                current_price=await pricing_service.get_price(session, s.unit_type_id, d),
                suggested_price=s.suggested_price,
            )
            for d in future
            if d not in busy
        ]
        views.append(
            SuggestionView(
                suggestion=s,
                nights=nights,
                occupied_count=len(future) - len(nights),
                total_nights=len(future),
            )
        )
    return views


# --------- lote: vista previa ---------


def _fingerprint(ids: list[int], items: list[BatchPreviewItem]) -> str:
    raw = ",".join(str(i) for i in sorted(set(ids))) + "#" + ";".join(
        f"{i.date.isoformat()}|{i.suggestion_id}|{i.old_price}|{i.new_price}|{i.valid}|{i.reason}"
        for i in items
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def preview_batch(
    session: AsyncSession, suggestion_ids: list[int], *, today: date | None = None
) -> BatchPreview:
    today = today or date.today()
    ids = sorted(set(suggestion_ids))
    sugs = await _load(session, ids, None)
    occ = await _occupancy_for(session, sugs, today)

    # Conflicto: dos seleccionadas que cubren la misma noche (futura) → ninguna se aplica.
    owners: dict[tuple[int, date], int] = {}
    conflicts: set[tuple[int, date]] = set()
    for s in sugs:
        if s.status not in _PENDING or s.unit_type_id is None:
            continue
        for d in _days(max(s.date_from, today), s.date_to):
            key = (s.unit_type_id, d)
            if key in owners and owners[key] != s.id:
                conflicts.add(key)
            owners[key] = s.id

    rules: dict[int, tuple[Decimal | None, Decimal | None] | None] = {}
    items: list[BatchPreviewItem] = []
    for s in sugs:
        resolved = s.status not in _PENDING or s.unit_type_id is None
        if s.unit_type_id is not None and s.unit_type_id not in rules:
            unit = await session.get(UnitType, s.unit_type_id)
            rule = await pricing_service.get_active_rule(session, unit.property_id)
            rules[s.unit_type_id] = (rule.min_price, rule.max_price) if rule else None
        bounds = rules.get(s.unit_type_id) if s.unit_type_id is not None else None
        out_of_bounds = bool(bounds and violates_rule(s.suggested_price, bounds[0], bounds[1]))
        busy = occ.get(s.unit_type_id, {}) if s.unit_type_id is not None else {}
        for d in _days(s.date_from, s.date_to):
            old = (
                await pricing_service.get_price(session, s.unit_type_id, d)
                if s.unit_type_id is not None
                else None
            )
            if resolved:
                reason = "sugerencia resuelta"
            elif d < today:
                reason = "pasada"
            elif d in busy:
                reason = busy[d]
            elif (s.unit_type_id, d) in conflicts:
                reason = "conflicto"
            elif out_of_bounds:
                reason = "fuera de límites"
            else:
                reason = None
            items.append(
                BatchPreviewItem(
                    date=d,
                    suggestion_id=s.id,
                    old_price=old,
                    new_price=s.suggested_price,
                    valid=reason is None,
                    reason=reason,
                )
            )
    items.sort(key=lambda i: (i.date, i.suggestion_id))
    valid = sum(1 for i in items if i.valid)
    return BatchPreview(
        suggestion_ids=ids,
        items=items,
        fingerprint=_fingerprint(ids, items),
        valid_count=valid,
        skipped_count=len(items) - valid,
    )


# --------- lote: aplicación ---------


def _tramos(items: list[BatchPreviewItem], unit_of: dict[int, int]):
    """Agrupa noches válidas en tramos contiguos de igual (unidad, precio)."""
    tramos: list[list[BatchPreviewItem]] = []
    for it in sorted(items, key=lambda i: (unit_of[i.suggestion_id], i.date)):
        last = tramos[-1][-1] if tramos else None
        if (
            last is not None
            and unit_of[last.suggestion_id] == unit_of[it.suggestion_id]
            and last.new_price == it.new_price
            and last.date + timedelta(days=1) == it.date
        ):
            tramos[-1].append(it)
        else:
            tramos.append([it])
    return tramos


async def apply_batch(
    session: AsyncSession,
    channel,
    suggestion_ids: list[int],
    fingerprint: str,
    *,
    today: date | None = None,
) -> BatchResult:
    today = today or date.today()
    preview = await preview_batch(session, suggestion_ids, today=today)
    if preview.fingerprint != fingerprint:
        return BatchResult(stale=True)

    sugs = {s.id: s for s in await _load(session, preview.suggestion_ids, None)}
    unit_of = {sid: s.unit_type_id for sid, s in sugs.items() if s.unit_type_id is not None}
    result = BatchResult()
    for it in preview.items:
        if not it.valid:
            result.nights.append(BatchResultNight(it.date, it.suggestion_id, "skipped", it.reason))

    for tramo in _tramos([i for i in preview.items if i.valid], unit_of):
        unit_id = unit_of[tramo[0].suggestion_id]
        unit = await session.get(UnitType, unit_id)
        failure: str | None = None
        try:
            async with session.begin_nested():
                for it in tramo:
                    await pricing_service.set_base_price(
                        session,
                        unit_type_id=unit_id,
                        day=it.date,
                        new_price=it.new_price,
                        origin=ChangeOrigin.suggestion,
                        property_id=unit.property_id,
                        suggestion_id=it.suggestion_id,
                        validate_rule=False,
                    )
                _published, issues = await pricing_app_service.publish_effective(
                    session, channel, unit_id, [it.date for it in tramo]
                )
                if issues:
                    # Salir con excepción revierte el SAVEPOINT (precio local intacto).
                    raise _TramoNoPublicado
        except _TramoNoPublicado:
            failure = "no se pudo publicar al canal"
        except Exception as exc:  # noqa: BLE001 — cualquier fallo del tramo lo revierte
            failure = f"error al publicar ({type(exc).__name__})"
        if failure:
            session.add(
                SyncIssue(
                    kind=SyncIssueKind.comm_error,
                    entity_ref=(
                        f"suggestion-batch:{tramo[0].date.isoformat()}..{tramo[-1].date.isoformat()}"
                    ),
                    detail=failure,
                )
            )
            await session.flush()
        status = "failed" if failure else "applied"
        for it in tramo:
            result.nights.append(BatchResultNight(it.date, it.suggestion_id, status, failure))

    result.nights.sort(key=lambda n: (n.date, n.suggestion_id))
    for sid in preview.suggestion_ids:
        mine = [n for n in result.nights if n.suggestion_id == sid]
        applied = [n for n in mine if n.status == "applied"]
        failed = [n for n in mine if n.status == "failed"]
        sug = sugs.get(sid)
        if applied and not failed and sug is not None:
            first = await session.execute(
                select(PriceChangeLog.id)
                .where(PriceChangeLog.suggestion_id == sid)
                .order_by(PriceChangeLog.id)
            )
            sug.applied_change_id = first.scalars().first()
            sug.status = SuggestionStatus.applied
            result.suggestions[sid] = "applied"
        elif failed:
            result.suggestions[sid] = "pending"
        else:
            result.suggestions[sid] = "unchanged"
    await session.flush()
    return result
