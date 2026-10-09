"""Dominio puro de la extensión de precios (feature 023).

Plantilla por año-mes propuesta desde los precios conocidos (mediana del mismo
mes del año sin noches de evento; si no hay, mediana global) y precio por noche
(% opcional de fin de semana, redondeo a miles, ajuste al [mínimo, máximo]).
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Literal

THOUSAND = Decimal(1000)
WEEKEND = (4, 5)  # noches de viernes y sábado

Clipped = Literal["min", "max"] | None


def round_1000(value: Decimal) -> Decimal:
    """Redondea al millar de COP más cercano."""
    return (value / THOUSAND).quantize(Decimal(1), rounding=ROUND_HALF_UP) * THOUSAND


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def is_weekend(day: date) -> bool:
    return day.weekday() in WEEKEND


def propose_template(
    known: dict[date, Decimal],
    event_days: set[date],
    months: list[str],
    fallback: Decimal | None = None,
) -> dict[str, Decimal | None]:
    """Precio propuesto por año-mes ("YYYY-MM").

    `known` = precios base conocidos (> 0) de cualquier fecha. Las noches con
    evento se excluyen para que los picos no contaminen la plantilla.
    """
    clean = [(d, p) for d, p in known.items() if p > 0 and d not in event_days]
    by_month: dict[int, list[Decimal]] = {}
    for d, p in clean:
        by_month.setdefault(d.month, []).append(p)
    overall = round_1000(Decimal(median([p for _, p in clean]))) if clean else None
    out: dict[str, Decimal | None] = {}
    for key in months:
        values = by_month.get(int(key[5:7]))
        if values:
            out[key] = round_1000(Decimal(median(values)))
        else:
            out[key] = overall if overall is not None else fallback
    return out


def night_price(
    template: Decimal,
    day: date,
    weekend_pct: Decimal,
    min_price: Decimal | None,
    max_price: Decimal | None,
) -> tuple[Decimal, Clipped]:
    """Precio de la noche y si quedó ajustado al mínimo o al máximo."""
    raw = template * (1 + weekend_pct / 100) if is_weekend(day) else template
    price = round_1000(raw)
    if min_price is not None and price < min_price:
        return min_price, "min"
    if max_price is not None and price > max_price:
        return max_price, "max"
    return price, None


def add_months(day: date, months: int) -> date:
    """Mismo día `months` meses después (ajustado al último día del mes si no existe)."""
    y, m = divmod(day.month - 1 + months, 12)
    year, month = day.year + y, m + 1
    for d in (day.day, 30, 29, 28):
        try:
            return date(year, month, min(day.day, d))
        except ValueError:
            continue
    return date(year, month, 28)
