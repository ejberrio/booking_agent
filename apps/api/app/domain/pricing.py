"""Lógica pura de precios (sin I/O). Núcleo testeable sin base de datos.

Reglas (de la spec y clarificaciones):
- Promociones solapadas: gana la de MAYOR descuento efectivo; no se acumulan.
- El precio efectivo nunca baja de 0.
- Los límites min/max de la regla validan el PRECIO BASE que fija el host
  (`violates_rule`); no recortan el efectivo tras promoción.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.enums import PromotionType


@dataclass(frozen=True)
class PromotionLike:
    """Vista mínima de una promoción para el cálculo (independiente del ORM)."""

    discount_type: PromotionType
    discount_value: Decimal
    start_date: date
    end_date: date
    active: bool = True

    def covers(self, day: date) -> bool:
        return self.active and self.start_date <= day <= self.end_date

    def discount_for(self, base_price: Decimal) -> Decimal:
        """Monto de descuento que esta promoción aplica sobre `base_price`."""
        if self.discount_type is PromotionType.percent:
            return (base_price * self.discount_value / Decimal(100)).quantize(Decimal("0.01"))
        return min(self.discount_value, base_price)


def best_promotion(
    promotions: list[PromotionLike], base_price: Decimal, day: date
) -> PromotionLike | None:
    """Promoción de mayor descuento vigente en `day`, o None."""
    applicable = [p for p in promotions if p.covers(day)]
    if not applicable:
        return None
    return max(applicable, key=lambda p: p.discount_for(base_price))


def effective_price(
    base_price: Decimal, promotions: list[PromotionLike], day: date
) -> Decimal:
    """Precio efectivo de un día: base menos la mejor promoción (sin acumular), piso en 0."""
    promo = best_promotion(promotions, base_price, day)
    if promo is None:
        return base_price
    result = base_price - promo.discount_for(base_price)
    return result if result > 0 else Decimal("0.00")


def violates_rule(
    price: Decimal, min_price: Decimal | None, max_price: Decimal | None
) -> bool:
    """True si `price` queda fuera del rango [min_price, max_price] de la regla."""
    if min_price is not None and price < min_price:
        return True
    if max_price is not None and price > max_price:
        return True
    return False
