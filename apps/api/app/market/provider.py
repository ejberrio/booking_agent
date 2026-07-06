"""Puerto de datos de mercado (feature 018, estrategia "Ambos").

Implementaciones: TavilyMarketProvider (gratis, búsquedas dirigidas) y, a futuro,
un proveedor pago (PriceLabs — ver ADR 0006). `None` = sin datos (honesto: el
motor no inventa números de mercado).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class MarketSnapshot:
    zone: str
    month: date  # primer día del mes consultado
    adr: Decimal | None  # tarifa diaria mediana de la zona; None = sin dato
    occupancy_pct: Decimal | None  # None = el proveedor no la da (gratis: siempre None)
    sample_size: int
    source: str

    @property
    def low_confidence(self) -> bool:
        return self.sample_size < 3


class MarketDataProvider(Protocol):
    async def get_snapshot(self, zone: str, month: date) -> MarketSnapshot | None: ...
