"""Objetos de valor transitorios del motor de precios (no ORM)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal


@dataclass
class RangeSelection:
    """Criterio de selección de días para una operación de rango."""

    date_from: date
    date_to: date
    weekdays: list[int] | None = None  # 0=lunes … 6=domingo; None = todos
    days: list[date] | None = None  # lista explícita; si se da, tiene prioridad

    def expand(self) -> list[date]:
        if self.days:
            return sorted(set(self.days))
        out: list[date] = []
        d = self.date_from
        while d <= self.date_to:
            if self.weekdays is None or d.weekday() in self.weekdays:
                out.append(d)
            d += timedelta(days=1)
        return out


@dataclass
class CalendarDayView:
    date: date
    base_price: Decimal | None
    effective_price: Decimal | None
    available: int | None  # None = sin datos sincronizados (no confundir con 0 = sin disponibilidad)
    promotions: list[str] = field(default_factory=list)


@dataclass
class ChangePreviewDay:
    date: date
    old_price: Decimal | None
    new_price: Decimal
    valid: bool
    reason: str | None = None


@dataclass
class ChangePreview:
    items: list[ChangePreviewDay]
    fingerprint: str
    has_invalid: bool
    valid_count: int
    invalid_count: int


@dataclass
class ApplyResult:
    applied_days: list[date] = field(default_factory=list)
    skipped_invalid: list[date] = field(default_factory=list)
    audited: int = 0
    published: int = 0
    publish_issues: int = 0
    stale: bool = False


def fingerprint_for(items: list[ChangePreviewDay]) -> str:
    """Huella estable del estado base afectado, para detectar previews obsoletos."""
    raw = ";".join(f"{i.date.isoformat()}={i.old_price}" for i in items)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
