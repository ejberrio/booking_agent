"""Agrupación PURA de sugerencias vendibles en bloques (feature 019, sin I/O).

- Con factor `event` → bloque `event:<nombre>`: une todas las sugerencias del mismo
  evento aunque sus noches no sean contiguas (p. ej. Martin Garrix 1 y 5 dic).
- Sin evento → bloque `period:<kind>:<inicio>` por la razón principal (`gap` = libre
  próximo, `occupancy` = ocupación alta, `other`), uniendo solo noches contiguas.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol

_PERIOD_TITLES = {"gap": "Libre próximo", "occupancy": "Ocupación alta", "other": "Otras"}


class _Night(Protocol):
    date: date
    suggestion_id: int
    current_price: Decimal | None
    suggested_price: Decimal


@dataclass(frozen=True)
class BlockInput:
    """Una sugerencia vendible: sus noches y sus factores (rationale.factors)."""

    suggestion_id: int
    nights: list  # list[_Night], ordenadas por fecha
    factors: list[dict] = field(default_factory=list)


@dataclass
class SuggestionBlock:
    key: str
    kind: str  # "event" | "period"
    title: str
    nights: list = field(default_factory=list)
    suggestion_ids: list[int] = field(default_factory=list)

    @property
    def date_from(self) -> date:
        return self.nights[0].date

    @property
    def date_to(self) -> date:
        return self.nights[-1].date

    @property
    def direction(self) -> str:
        ups = downs = 0
        for n in self.nights:
            if n.current_price is None or n.suggested_price == n.current_price:
                continue
            if n.suggested_price > n.current_price:
                ups += 1
            else:
                downs += 1
        if ups and downs:
            return "mixed"
        return "down" if downs else "up"


def _normalize(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(plain.lower().split())


def _event_name(factors: list[dict]) -> str | None:
    for f in factors:
        if f.get("kind") == "event":
            ev = f.get("event") or {}
            return ev.get("name") or f.get("label")
    return None


def _period_kind(factors: list[dict]) -> str:
    kinds = {f.get("kind") for f in factors}
    if "occupancy" in kinds:
        return "occupancy"
    if "gap" in kinds:
        return "gap"
    return "other"


def build_blocks(inputs: list[BlockInput]) -> list[SuggestionBlock]:
    events: dict[str, SuggestionBlock] = {}
    periods: list[SuggestionBlock] = []
    # Noches de periodo por tipo, para unir solo las contiguas.
    pending: dict[str, list[tuple[object, int]]] = {}

    for inp in inputs:
        if not inp.nights:
            continue
        name = _event_name(inp.factors)
        if name:
            key = f"event:{_normalize(name)}"
            block = events.setdefault(key, SuggestionBlock(key=key, kind="event", title=name))
            block.nights.extend(inp.nights)
            block.suggestion_ids.append(inp.suggestion_id)
        else:
            kind = _period_kind(inp.factors)
            pending.setdefault(kind, []).extend((n, inp.suggestion_id) for n in inp.nights)

    for kind, nights in pending.items():
        nights.sort(key=lambda t: t[0].date)
        current: SuggestionBlock | None = None
        for night, sid in nights:
            if current is None or current.nights[-1].date + timedelta(days=1) != night.date:
                current = SuggestionBlock(
                    key=f"period:{kind}:{night.date.isoformat()}",
                    kind="period",
                    title=_PERIOD_TITLES[kind],
                )
                periods.append(current)
            current.nights.append(night)
            if sid not in current.suggestion_ids:
                current.suggestion_ids.append(sid)

    blocks = list(events.values()) + periods
    for b in blocks:
        b.nights.sort(key=lambda n: n.date)
    blocks.sort(key=lambda b: (b.date_from, b.key))
    return blocks
