"""Heurística PURA de sugerencia de precio (sin I/O). Explicable y configurable."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import Relevance

D = Decimal

EVENT_UPLIFT = {Relevance.high: D("0.30"), Relevance.medium: D("0.15"), Relevance.low: D("0.05")}
OCCUPANCY_UPLIFT = D("0.10")
_CONFIDENCE = {1: D("0.5"), 2: D("0.7"), 3: D("0.9")}


@dataclass(frozen=True)
class SuggestionOutput:
    price: Decimal
    justification: str
    confidence: Decimal


def suggest_price(
    base: Decimal,
    *,
    event_relevance: Relevance | None,
    occupancy_high: bool,
    market_ref: Decimal | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
) -> SuggestionOutput | None:
    """Devuelve una sugerencia, o None si no hay señales o el cambio es nulo."""
    if event_relevance is None and not occupancy_high and market_ref is None:
        return None

    factor = D("0")
    reasons: list[str] = []
    if event_relevance is not None:
        up = EVENT_UPLIFT[event_relevance]
        factor += up
        reasons.append(f"evento {event_relevance.value} (+{int(up * 100)}%)")
    if occupancy_high:
        factor += OCCUPANCY_UPLIFT
        reasons.append("ocupación alta (+10%)")

    target = (base * (D("1") + factor)).quantize(D("1"))
    if market_ref is not None:
        target = ((target + market_ref) / D("2")).quantize(D("1"))
        reasons.append(f"referencia de mercado {market_ref}")

    if min_price is not None and target < min_price:
        target = min_price
    if max_price is not None and target > max_price:
        target = max_price

    if target == base:
        return None  # sin cambio significativo

    signals = sum([event_relevance is not None, occupancy_high, market_ref is not None])
    return SuggestionOutput(target, "; ".join(reasons), _CONFIDENCE.get(signals, D("0.5")))
