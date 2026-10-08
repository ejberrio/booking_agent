"""Precio de una promoción que nace de una bajada sugerida (feature 022). PURO.

El precio base no se toca: la bajada se publica como promoción. Si el host definió un
precio mínimo por noche, la promoción se recorta para que el precio que pagaría el
huésped en CADA canal, restando los descuentos que siempre pueden acumularse (p. ej.
el 10 % por reservar desde el celular), no quede por debajo del mínimo:

    precio_promo ≥ max(mínimo, máx_c mínimo / (1 − a_c))

La promoción es UNA para Booking.com y Airbnb, así que manda el canal más exigente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

D = Decimal
MIN_PCT = D("1")  # una promoción de menos de 1 % no vale la pena

SKIP_BELOW_MIN = "por debajo del precio mínimo"
SKIP_TOO_SMALL = "menos de 1 %"


@dataclass(frozen=True)
class PromoPlan:
    price: Decimal | None  # precio con promoción (None = noche omitida)
    pct: Decimal | None  # % de descuento sobre el base (1 decimal)
    clipped: bool = False  # recortado por el precio mínimo
    final_by_channel: dict[str, Decimal] = field(default_factory=dict)
    skip_reason: str | None = None


def _ceil_cop(v: Decimal) -> Decimal:
    return v.quantize(D("1"), rounding=ROUND_CEILING)


def plan_promo(
    base: Decimal,
    suggested: Decimal,
    min_price: Decimal | None,
    always_pct_by_channel: dict[str, Decimal],
) -> PromoPlan:
    """Plan de promoción para una noche con `suggested < base`."""
    price = suggested
    clipped = False
    if min_price is not None:
        if min_price >= base:
            return PromoPlan(None, None, skip_reason=SKIP_BELOW_MIN)
        floor = min_price
        for pct in always_pct_by_channel.values():
            keep = D(1) - pct / D(100)
            if keep > 0:
                floor = max(floor, min_price / keep)
        floor = _ceil_cop(floor)
        if price < floor:
            price, clipped = floor, True
    pct = ((base - price) / base * D(100)).quantize(D("0.1"), rounding=ROUND_HALF_UP)
    if pct < MIN_PCT:
        return PromoPlan(
            None, None, clipped=clipped, skip_reason=SKIP_BELOW_MIN if clipped else SKIP_TOO_SMALL
        )
    finals = {
        ch: (price * (D(1) - a / D(100))).quantize(D("1"), rounding=ROUND_HALF_UP)
        for ch, a in always_pct_by_channel.items()
    }
    return PromoPlan(price, pct, clipped, finals)
