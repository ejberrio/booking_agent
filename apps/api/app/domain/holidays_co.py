"""Festivos de Colombia y puentes (feature 034), sin dependencias externas.

Reglas (Ley 51 de 1983 "Ley Emiliani", Ley 2578 de 2026):
- Fijos: 1 ene, 1 may, 20 jul, 7 ago, 8 dic, 25 dic.
- Se corren al lunes siguiente: 6 ene, 19 mar, 29 jun, 9 jul (Chiquinquirá, desde 2026),
  15 ago, 12 oct, 1 nov, 11 nov.
- Según la Pascua: Jueves y Viernes Santo (fijos); Ascensión (+43), Corpus Christi (+64) y
  Sagrado Corazón (+71), ya corridos al lunes.

Verificado contra date.nager.at para 2026 y 2027 (19 festivos cada año).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

_FIXED = [(1, 1, "Año Nuevo"), (5, 1, "Día del Trabajo"), (7, 20, "Independencia"),
          (8, 7, "Batalla de Boyacá"), (12, 8, "Inmaculada Concepción"), (12, 25, "Navidad")]
_MOVED = [(1, 6, "Reyes Magos"), (3, 19, "San José"), (6, 29, "San Pedro y San Pablo"),
          (8, 15, "Asunción de la Virgen"), (10, 12, "Día de la Raza"),
          (11, 1, "Todos los Santos"), (11, 11, "Independencia de Cartagena")]
_MOVED_FROM_2026 = [(7, 9, "Virgen de Chiquinquirá")]


def easter(year: int) -> date:
    """Domingo de Pascua (algoritmo de Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = (h + l_ - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7)


def holidays(year: int) -> dict[date, str]:
    out: dict[date, str] = {date(year, m, d): n for m, d, n in _FIXED}
    moved = _MOVED + (_MOVED_FROM_2026 if year >= 2026 else [])
    for m, d, n in moved:
        out[_next_monday(date(year, m, d))] = n
    e = easter(year)
    out[e - timedelta(days=3)] = "Jueves Santo"
    out[e - timedelta(days=2)] = "Viernes Santo"
    out[e + timedelta(days=43)] = "Ascensión del Señor"
    out[e + timedelta(days=64)] = "Corpus Christi"
    out[e + timedelta(days=71)] = "Sagrado Corazón"
    return dict(sorted(out.items()))


@dataclass(frozen=True)
class LongWeekend:
    name: str
    first_night: date  # noche de llegada (inclusive)
    last_night: date  # última noche (la salida es al día siguiente)
    high: bool  # Semana Santa y fin de año: demanda más alta


def long_weekends(start: date, end: date) -> list[LongWeekend]:
    """Fines de semana largos (puentes) y Semana Santa entre `start` y `end`.

    Noches que importan para el precio: si el festivo es lunes, las de viernes, sábado y
    domingo; si es viernes, jueves a domingo; un festivo suelto entre semana, la noche anterior.
    """
    out: list[LongWeekend] = []
    for year in range(start.year, end.year + 1):
        e = easter(year)
        for day, name in holidays(year).items():
            if name in ("Jueves Santo", "Viernes Santo"):
                continue
            wd = day.weekday()
            if wd == 0:  # lunes → viernes, sábado y domingo
                first, last = day - timedelta(days=3), day - timedelta(days=1)
            elif wd == 4:  # viernes → jueves a domingo
                first, last = day - timedelta(days=1), day + timedelta(days=1)
            elif wd in (5, 6):  # cae en fin de semana: no agrega noches
                continue
            else:
                first = last = day - timedelta(days=1)
            out.append(LongWeekend(f"Puente festivo: {name}", first, last,
                                   high=name in ("Navidad", "Año Nuevo")))
        # Semana Santa: del miércoles al domingo de Pascua (alta demanda en destinos turísticos)
        out.append(LongWeekend("Semana Santa", e - timedelta(days=4), e - timedelta(days=1),
                               high=True))
    return sorted((w for w in out if w.last_night >= start and w.first_night <= end),
                  key=lambda w: w.first_night)
