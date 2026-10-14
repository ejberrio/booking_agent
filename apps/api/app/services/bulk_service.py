"""Cambios en bloque del asistente (feature 032).

El servidor calcula el resultado de CADA noche (el modelo de lenguaje no hace cuentas):

- `plan_price_change` / `apply_price_change`: fijar un precio, subir o bajar un porcentaje
  o un monto en un rango (con días de semana) o en fechas sueltas. Omite noches pasadas,
  reservadas o bloqueadas, sin precio, fuera de los límites del host o con una variación
  mayor a ±50 %. Se publica por tramos contiguos de igual precio, cada uno en un SAVEPOINT.
- `plan_discount` / `apply_discount`: descuento sobre el precio de CADA noche, publicado como
  promociones (una por tramo contiguo de igual base y precio con descuento). Respeta el precio
  mínimo y los descuentos que siempre se acumulan (`plan_promo`, feature 022) y reúne los
  avisos de `offer_promotion_service.preview` (solapes, reservas, doble descuento).

Ambos devuelven una huella: si el estado cambia entre la propuesta y la confirmación, no se
aplica nada y el asistente vuelve a proponer (principio III).
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.pricing import violates_rule
from app.domain.promo_floor import plan_promo
from app.models.enums import ChangeOrigin, SyncIssueKind
from app.models.property import Property, UnitType
from app.models.sync import SyncIssue
from app.schemas.pricing import RangeSelection
from app.services import native_deal_service, pricing_app_service, pricing_service
from app.services.suggestion_batch import occupied_nights

D = Decimal
MAX_NIGHTS = 366
MAX_TRAMOS = 31
MAX_VARIATION = D("0.5")

PAST = "pasada"
NO_PRICE = "sin precio"
OUT_OF_BOUNDS = "fuera de límites"
TOO_BIG = "variación mayor a 50 %"
NO_CHANGE = "sin cambio"
INVALID = "precio inválido"
NOT_LOWER = "no es menor que el precio"


class BulkError(ValueError):
    """Solicitud inválida: el asistente recibe el mensaje y se corrige."""


@dataclass(frozen=True)
class Night:
    date: date
    old: Decimal | None
    new: Decimal | None
    valid: bool
    reason: str | None = None
    pct: Decimal | None = None  # descuento: % sobre el base de la noche
    clipped: bool = False  # descuento: recortado por el precio mínimo


@dataclass
class Plan:
    kind: str  # "price" | "discount"
    unit_type_id: int
    nights: list[Night]
    fingerprint: str
    currency: str = "COP"
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> list[Night]:
        return [n for n in self.nights if n.valid]

    @property
    def skipped(self) -> dict[str, int]:
        return dict(Counter(n.reason or "" for n in self.nights if not n.valid))

    def tramos(self) -> list[list[Night]]:
        """Noches válidas contiguas con igual (antes, después)."""
        out: list[list[Night]] = []
        for n in self.valid:
            last = out[-1][-1] if out else None
            if (
                last is not None
                and last.date + timedelta(days=1) == n.date
                and last.old == n.old
                and last.new == n.new
            ):
                out[-1].append(n)
            else:
                out.append([n])
        return out


@dataclass
class ApplyReport:
    stale: bool = False
    applied: int = 0
    failed: int = 0
    tramos: int = 0
    promotions: list[int] = field(default_factory=list)


# --------- utilidades ---------


def _round(value: Decimal, step: int | None) -> Decimal:
    if step and step > 1:
        return (value / step).quantize(D("1"), rounding=ROUND_HALF_UP) * step
    return value.quantize(D("1"), rounding=ROUND_HALF_UP)


def nights_for(
    date_from: date | None, date_to: date | None, weekdays: list[int] | None, dates: list[date] | None
) -> list[date]:
    if dates:
        out = sorted(set(dates))
    else:
        if date_from is None or date_to is None:
            raise BulkError("indica date_from y date_to, o una lista de fechas en 'dates'.")
        if date_to < date_from:
            raise BulkError("date_to no puede ser anterior a date_from.")
        out = RangeSelection(date_from, date_to, weekdays=weekdays).expand()
    if not out:
        raise BulkError("la selección no tiene noches (revisa el rango y los días de semana).")
    if len(out) > MAX_NIGHTS:
        raise BulkError(f"máximo {MAX_NIGHTS} noches por propuesta; divide la solicitud.")
    return out


def _fingerprint(kind: str, unit_type_id: int, nights: list[Night], extra: str = "") -> str:
    raw = f"{kind}|{unit_type_id}|" + ";".join(
        f"{n.date.isoformat()}={n.old}>{n.new}:{n.valid}:{n.reason}" for n in nights
    ) + "|" + extra
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def _context(session: AsyncSession, unit_type_id: int):
    unit = await session.get(UnitType, unit_type_id)
    if unit is None:
        raise BulkError(f"la unidad {unit_type_id} no existe")
    prop = await session.get(Property, unit.property_id)
    rule = await pricing_service.get_active_rule(session, unit.property_id)
    return unit, (prop.currency if prop else "COP"), rule


# --------- cambio de precio ---------


async def plan_price_change(
    session: AsyncSession,
    *,
    unit_type_id: int,
    mode: str,
    value: Decimal,
    date_from: date | None = None,
    date_to: date | None = None,
    weekdays: list[int] | None = None,
    dates: list[date] | None = None,
    round_to: int | None = None,
    today: date | None = None,
) -> Plan:
    if mode not in ("set", "percent", "amount"):
        raise BulkError("mode debe ser set, percent o amount.")
    if mode == "set" and value <= 0:
        raise BulkError("el precio debe ser mayor que 0.")
    if mode == "percent" and not (D(-90) <= value <= D(300)):
        raise BulkError("el porcentaje debe estar entre -90 y 300.")
    today = today or date.today()
    days = nights_for(date_from, date_to, weekdays, dates)
    unit, currency, rule = await _context(session, unit_type_id)
    busy = await occupied_nights(session, unit_type_id, days[0], days[-1])
    prices = await pricing_service.get_prices(session, unit_type_id, days[0], days[-1])
    nights: list[Night] = []
    for d in days:
        old = prices.get(d)
        if d < today:
            nights.append(Night(d, old, None, False, PAST))
            continue
        if d in busy:
            nights.append(Night(d, old, None, False, busy[d]))
            continue
        if old is None and mode != "set":
            nights.append(Night(d, None, None, False, NO_PRICE))
            continue
        if mode == "set":
            new = _round(value, round_to)
        elif mode == "percent":
            new = _round(old * (D(1) + value / D(100)), round_to)
        else:
            new = _round(old + value, round_to)
        reason = None
        if new <= 0:
            reason = INVALID
        elif rule and violates_rule(new, rule.min_price, rule.max_price):
            reason = OUT_OF_BOUNDS
        elif old and abs(new - old) / old > MAX_VARIATION:
            reason = TOO_BIG
        elif old == new:
            reason = NO_CHANGE
        nights.append(Night(d, old, new, reason is None, reason))
    return Plan("price", unit_type_id, nights, _fingerprint("price", unit_type_id, nights), currency)


async def apply_price_change(
    session: AsyncSession,
    channel,
    *,
    fingerprint: str,
    origin: ChangeOrigin = ChangeOrigin.chat,
    message_id: int | None = None,
    **params,
) -> ApplyReport:
    plan = await plan_price_change(session, **params)
    if plan.fingerprint != fingerprint:
        return ApplyReport(stale=True)
    unit = await session.get(UnitType, plan.unit_type_id)
    report = ApplyReport()
    for tramo in plan.tramos():
        failure = None
        try:
            async with session.begin_nested():
                for n in tramo:
                    await pricing_service.set_base_price(
                        session,
                        unit_type_id=plan.unit_type_id,
                        day=n.date,
                        new_price=n.new,
                        origin=origin,
                        property_id=unit.property_id,
                        message_id=message_id,
                        validate_rule=False,
                    )
                _pub, issues = await pricing_app_service.publish_effective(
                    session, channel, plan.unit_type_id, [n.date for n in tramo]
                )
                if issues:
                    raise _NotPublished
        except _NotPublished:
            failure = "no se pudo publicar al canal"
        except Exception as exc:  # noqa: BLE001 — el tramo falla solo y se revierte
            failure = f"error al publicar ({type(exc).__name__})"
        report.tramos += 1
        if failure:
            report.failed += len(tramo)
            await _issue(session, f"chat-price:{tramo[0].date}..{tramo[-1].date}", failure)
        else:
            report.applied += len(tramo)
    return report


class _NotPublished(Exception):
    pass


async def _issue(session: AsyncSession, ref: str, detail: str) -> None:
    session.add(SyncIssue(kind=SyncIssueKind.comm_error, entity_ref=ref, detail=detail))
    await session.flush()


# --------- descuento (promociones por tramo) ---------


async def plan_discount(
    session: AsyncSession,
    adapter,
    *,
    unit_type_id: int,
    name: str,
    discount_pct: Decimal | None = None,
    price: Decimal | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    weekdays: list[int] | None = None,
    dates: list[date] | None = None,
    min_nights: int | None = None,
    channels_scope: list[str] | None = None,
    today: date | None = None,
) -> Plan:
    from app.services import offer_promotion_service

    if (discount_pct is None) == (price is None):
        raise BulkError("indica el descuento en discount_pct o el precio con descuento en price.")
    if discount_pct is not None and not (D(0) < discount_pct < D(100)):
        raise BulkError("el descuento debe estar entre 0 y 100 %.")
    if price is not None and price <= 0:
        raise BulkError("el precio con descuento debe ser mayor que 0.")
    today = today or date.today()
    days = nights_for(date_from, date_to, weekdays, dates)
    unit, currency, rule = await _context(session, unit_type_id)
    min_price = rule.min_price if rule else None
    busy = await occupied_nights(session, unit_type_id, days[0], days[-1])
    prices = await pricing_service.get_prices(session, unit_type_id, days[0], days[-1])
    nights: list[Night] = []
    for d in days:
        base = prices.get(d)
        if d < today:
            nights.append(Night(d, base, None, False, PAST))
            continue
        if d in busy:
            nights.append(Night(d, base, None, False, busy[d]))
            continue
        if base is None:
            nights.append(Night(d, None, None, False, NO_PRICE))
            continue
        target = (
            _round(base * (D(1) - discount_pct / D(100)), None) if discount_pct is not None
            else _round(price, None)
        )
        if target >= base:
            nights.append(Night(d, base, None, False, NOT_LOWER))
            continue
        always = await native_deal_service.always_pct_for(session, d)
        promo = plan_promo(base, target, min_price, always)
        if promo.price is None:
            nights.append(Night(d, base, None, False, promo.skip_reason))
            continue
        nights.append(Night(d, base, promo.price, True, None, promo.pct, promo.clipped))
    plan = Plan("discount", unit_type_id, nights, "", currency)
    tramos = plan.tramos()
    if len(tramos) > MAX_TRAMOS:
        raise BulkError(
            f"el descuento quedaría en {len(tramos)} promociones (máximo {MAX_TRAMOS}); "
            "acota las fechas o los días."
        )
    warnings: list[str] = []
    for tramo in tramos:
        try:
            prev = await offer_promotion_service.preview(
                session,
                adapter,
                unit_type_id=unit_type_id,
                first_night=tramo[0].date,
                last_night=tramo[-1].date,
                name=name,
                price=tramo[0].new,
                min_nights=min_nights,
                channels_scope=channels_scope,
            )
        except offer_promotion_service.PromotionError as exc:
            raise BulkError(str(exc)) from exc
        for w in prev.warnings:
            if w not in warnings:
                warnings.append(w)
    if any(n.clipped for n in plan.valid):
        warnings.append("Algunas noches se recortaron para no quedar por debajo de tu precio mínimo.")
    plan.warnings = warnings
    plan.fingerprint = _fingerprint(
        "discount", unit_type_id, nights, f"{name}|{min_nights}|{channels_scope}|{warnings}"
    )
    return plan


def _range_label(first: date, last: date) -> str:
    return first.isoformat() if first == last else f"{first.isoformat()}..{last.isoformat()}"


async def apply_discount(
    session: AsyncSession,
    channel,
    *,
    fingerprint: str,
    origin: ChangeOrigin = ChangeOrigin.chat,
    **params,
) -> ApplyReport:
    from app.services import offer_promotion_service

    plan = await plan_discount(session, channel, **params)
    if plan.fingerprint != fingerprint:
        return ApplyReport(stale=True)
    report = ApplyReport()
    tramos = plan.tramos()
    for tramo in tramos:
        name = params["name"]
        if len(tramos) > 1:
            name = f"{name} · {_range_label(tramo[0].date, tramo[-1].date)}"
        failure = None
        try:
            async with session.begin_nested():
                res = await offer_promotion_service.apply(
                    session,
                    channel,
                    unit_type_id=plan.unit_type_id,
                    first_night=tramo[0].date,
                    last_night=tramo[-1].date,
                    name=name[:120],
                    price=tramo[0].new,
                    min_nights=params.get("min_nights"),
                    fingerprint=None,
                    confirm_overlap=True,  # el host confirmó viendo los avisos
                    origin=origin,
                    channels_scope=params.get("channels_scope"),
                )
                if not res.published:
                    raise _NotPublished
                report.promotions.append(res.id)
        except _NotPublished:
            failure = "no se pudo publicar al canal"
        except Exception as exc:  # noqa: BLE001
            failure = f"error al publicar ({type(exc).__name__})"
        report.tramos += 1
        if failure:
            report.failed += len(tramo)
            await _issue(session, f"chat-discount:{tramo[0].date}..{tramo[-1].date}", failure)
        else:
            report.applied += len(tramo)
    return report
