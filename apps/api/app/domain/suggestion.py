"""Heurística PURA de sugerencia de precio v2 (sin I/O). Explicable y simétrica.

Señales alcistas (evento, ocupación alta de la ventana) y BAJISTAS (hueco libre
próximo — descuento progresivo: más cerca ⇒ mayor). El mercado actúa como ANCLA
(promedio ponderado: 50%, o 25% en fechas de evento) solo con muestras suficientes;
nunca se inventa. Límites SIEMPRE:
piso min_price, techo max_price y tope bajista −15% (decisión del host).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.market.provider import MarketSnapshot
from app.models.enums import Relevance

D = Decimal

EVENT_UPLIFT = {Relevance.high: D("0.30"), Relevance.medium: D("0.15"), Relevance.low: D("0.05")}
OCCUPANCY_UPLIFT = D("0.10")
MAX_DISCOUNT = D("0.15")  # tope bajista por sugerencia (host, clarify 2026-07-04)
GAP_WINDOW_DAYS = 14  # ventana de "hueco próximo" (host)
# Banda de credibilidad del mercado frente al precio base: fuera de ella el ADR no es
# comparable (p. ej. habitaciones sueltas, USD o por persona) y no se usa como ancla.
# Dentro de la banda SÍ puede bajar el precio (competencia más barata).
MARKET_PLAUSIBLE = (D("0.5"), D("2.0"))
# Peso del mercado al anclar: 50% por defecto; 25% en fechas de EVENTO para que el
# evento pese más sin ignorar al mercado (decisión del host, 2026-10-08).
MARKET_WEIGHT = D("0.5")
MARKET_WEIGHT_EVENT = D("0.25")
_CONFIDENCE = {1: D("0.5"), 2: D("0.7"), 3: D("0.9")}


@dataclass(frozen=True)
class EventSignal:
    """Metadatos del evento que justifica la señal (para el racional explicable)."""

    relevance: Relevance
    name: str
    location: str | None = None
    dates: str | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class Factor:
    kind: str  # "event" | "occupancy" | "gap" | "market"
    label: str
    pct: Decimal | None = None
    event: dict | None = None


@dataclass(frozen=True)
class SuggestionOutputV2:
    price: Decimal
    text: str  # resumen de una línea (compatible con el rationale.text v1)
    confidence: Decimal
    factors: list[Factor] = field(default_factory=list)


def _gap_discount(days_ahead: int) -> Decimal:
    """Descuento progresivo del hueco: más cerca ⇒ mayor, con tope MAX_DISCOUNT."""
    raw = D("0.03") + (D(GAP_WINDOW_DAYS) - D(days_ahead)) * D("0.01")
    return min(MAX_DISCOUNT, max(D("0.03"), raw))


def suggest_price_v2(
    base: Decimal,
    *,
    event: EventSignal | None = None,
    occupancy_high: bool = False,
    gap_days_ahead: int | None = None,
    market: MarketSnapshot | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
) -> SuggestionOutputV2 | None:
    """Sugerencia para un precio base, o None sin señales primarias / cambio nulo.

    El mercado por sí solo no dispara sugerencias (evita ruido); ancla las que
    disparan evento/ocupación/hueco.
    """
    if event is None and not occupancy_high and gap_days_ahead is None:
        return None

    factor_pct = D("0")
    factors: list[Factor] = []

    if event is not None:
        up = EVENT_UPLIFT[event.relevance]
        factor_pct += up
        factors.append(
            Factor(
                kind="event",
                label=f"{event.name} ({event.relevance.value}, +{int(up * 100)}%)",
                pct=up * 100,
                event={
                    "name": event.name,
                    "location": event.location,
                    "dates": event.dates,
                    "source_url": event.source_url,
                },
            )
        )
    if occupancy_high:
        factor_pct += OCCUPANCY_UPLIFT
        factors.append(Factor(kind="occupancy", label="ocupación alta alrededor (+10%)", pct=D("10")))
    if event is None and not occupancy_high and gap_days_ahead is not None:
        down = _gap_discount(gap_days_ahead)
        factor_pct -= down
        factors.append(
            Factor(
                kind="gap",
                label=f"libre a {gap_days_ahead} día{'s' if gap_days_ahead != 1 else ''} (−{int(down * 100)}%)",
                pct=-(down * 100),
            )
        )

    target = (base * (D("1") + factor_pct)).quantize(D("1"))

    # Ancla de mercado: solo con muestras suficientes; con pocas, informa sin anclar.
    market_ok = False
    if market is not None and market.adr is not None:
        lo, hi = base * MARKET_PLAUSIBLE[0], base * MARKET_PLAUSIBLE[1]
        if not (lo <= market.adr <= hi):
            factors.append(
                Factor(
                    kind="market",
                    label=(
                        f"mercado ~{market.adr:.0f} descartado: no es comparable con tu "
                        "tarifa (fuera del rango creíble)"
                    ),
                )
            )
        elif not market.low_confidence:
            market_ok = True
            weight = MARKET_WEIGHT_EVENT if event is not None else MARKET_WEIGHT
            target = (target * (D("1") - weight) + market.adr * weight).quantize(D("1"))
            factors.append(
                Factor(
                    kind="market",
                    label=(
                        f"mercado de la zona ~{market.adr:.0f} ({market.sample_size} tarifas, "
                        f"{market.source}; pesa {int(weight * 100)}%)"
                    ),
                )
            )
        else:
            factors.append(
                Factor(
                    kind="market",
                    label=(
                        f"mercado ~{market.adr:.0f} pero con solo {market.sample_size} "
                        "tarifa(s): confianza baja, no se usa como ancla"
                    ),
                )
            )

    # Límites SIEMPRE: tope bajista −15%, piso y techo de la regla.
    floor_discount = (base * (D("1") - MAX_DISCOUNT)).quantize(D("1"))
    if target < floor_discount:
        target = floor_discount
    if min_price is not None and target < min_price:
        target = min_price
    if max_price is not None and target > max_price:
        target = max_price

    if target == base:
        return None  # sin cambio significativo

    primary = sum([event is not None, occupancy_high, gap_days_ahead is not None])
    anchored = 1 if market_ok else 0
    confidence = _CONFIDENCE.get(min(3, primary + anchored), D("0.5"))
    text = "; ".join(f.label for f in factors)
    return SuggestionOutputV2(price=target, text=text, confidence=confidence, factors=factors)
