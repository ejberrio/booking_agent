"""Regla PURA de no repetición de sugerencias (sin I/O).

Problema: tras aplicar una sugerencia, el scan diario volvía a proponer lo mismo para
las mismas noches. Dos causas: (1) el motor calculaba sobre el precio YA subido y la
señal se volvía a sumar (130 → 169 → …), y (2) el antiduplicado solo reconocía una
sugerencia idéntica (mismo rango y mismo precio exactos).

Reglas por noche:
- Precio de referencia: el precio que fijó el host, deshaciendo la cadena de cambios
  que vinieron de sugerencias aplicadas (así la señal no se acumula).
- Precio actual ≈ sugerido (dentro de la tolerancia) → nada que sugerir.
- Noche ya decidida (aplicada o rechazada) → solo se vuelve a proponer si el cambio es
  DRÁSTICO: el nuevo precio difiere del ya decidido más que el umbral, o cambia de
  sentido (lo decidido subía y ahora baja, o al revés).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

D = Decimal


@dataclass(frozen=True)
class PriceLog:
    """Cambio de precio de una noche (de la bitácora), del más nuevo al más viejo."""

    old_price: Decimal | None
    new_price: Decimal
    from_suggestion: bool


@dataclass(frozen=True)
class PriorDecision:
    """Última decisión del host sobre una noche: sugerencia aplicada o rechazada."""

    suggestion_id: int
    status: str  # "applied" | "rejected"
    price: Decimal
    date_from: date
    date_to: date
    decided_on: date | None = None

    def as_dict(self, threshold_pct: Decimal) -> dict:
        """Forma serializable para el racional (la web muestra "ya aplicaste X el día Y")."""
        return {
            "suggestion_id": self.suggestion_id,
            "status": self.status,
            "price": str(self.price),
            "date_from": self.date_from.isoformat(),
            "date_to": self.date_to.isoformat(),
            "decided_on": self.decided_on.isoformat() if self.decided_on else None,
            "threshold_pct": float(threshold_pct),
        }


def reference_base(current: Decimal, logs: list[PriceLog]) -> Decimal:
    """Precio base "del host": deshace los cambios consecutivos que vinieron de sugerencias.

    Recorre la bitácora de la noche (más nuevo primero) mientras cada cambio sea de una
    sugerencia y encadene con el precio vigente. Se corta ante un cambio manual, uno sin
    precio anterior o uno que no encadena (p. ej. el precio cambió fuera de la app).
    """
    ref = current
    for log in logs:
        if not log.from_suggestion or log.old_price is None or log.new_price != ref:
            break
        ref = log.old_price
    return ref


def _sign(x: Decimal) -> int:
    return (x > 0) - (x < 0)


def same_price(a: Decimal, b: Decimal, tolerance_pct: Decimal) -> bool:
    """¿a y b son el mismo precio dentro de la tolerancia (porcentaje sobre b)?"""
    return abs(a - b) <= abs(b) * tolerance_pct / D(100)


def is_drastic(
    new_price: Decimal, prior_price: Decimal, reference: Decimal, threshold_pct: Decimal
) -> bool:
    """Cambio drástico frente a lo ya decidido: cambia de sentido o supera el umbral."""
    new_dir = _sign(new_price - reference)
    prior_dir = _sign(prior_price - reference)
    if new_dir and prior_dir and new_dir != prior_dir:
        return True
    return abs(new_price - prior_price) > abs(prior_price) * threshold_pct / D(100)


def should_propose(
    new_price: Decimal,
    *,
    current: Decimal,
    reference: Decimal,
    prior_price: Decimal | None,
    threshold_pct: Decimal,
    tolerance_pct: Decimal,
) -> bool:
    """¿Se propone `new_price` para la noche? (ver reglas en el docstring del módulo)."""
    if same_price(new_price, current, tolerance_pct):
        return False
    if prior_price is None:
        return True
    return is_drastic(new_price, prior_price, reference, threshold_pct)
