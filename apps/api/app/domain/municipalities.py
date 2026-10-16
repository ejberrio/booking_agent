"""Municipios de Colombia (feature 030): lista oficial DIVIPOLA (DANE) para el informe público.

`app/data/municipios_co.json` = [[código DANE, municipio, departamento], …] (1.122 filas,
generado desde datos.gov.co). La "ciudad" de un municipio es la clave con la que se guardan
sus eventos públicos (`event.city`, `event_service.normalize_city`): así lo que encuentra un
informe sirve después a las cuentas de ese municipio y viceversa.
"""

from __future__ import annotations

import json
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.services.event_service import normalize_city

_DATA = Path(__file__).resolve().parent.parent / "data" / "municipios_co.json"

# Nombre corto con el que la gente (y las cuentas) llaman al municipio.
_SHORT = {
    "76001": "Cali",
    "13001": "Cartagena",
    "13468": "Mompox",
}
# Nombres repetidos en varios departamentos: estos se quedan con la clave sin departamento
# (además de las capitales, código terminado en 001).
_PREFERRED = {"05615", "88001", "08573", "05129", "05079", "05212"}

# Área metropolitana → ciudad principal: el informe une los eventos de ambas.
_METRO_CORE = {
    "05001": ("05088", "05360", "05266", "05631", "05380", "05129", "05212", "05308", "05079"),
    "11001": ("25754", "25175", "25214", "25286", "25473", "25430", "25126", "25377", "25758",
              "25899", "25817"),
    "76001": ("76364", "76892", "76520", "76130"),
    "08001": ("08758", "08433", "08573", "08296"),
    "68001": ("68276", "68307", "68547"),
    "54001": ("54874", "54405", "54261"),
    "66001": ("66170", "66400"),
}
_CORE_OF = {member: core for core, members in _METRO_CORE.items() for member in members}


@dataclass(frozen=True)
class Municipality:
    code: str
    name: str
    department: str
    city: str  # nombre para buscar eventos ("Cali", "Sabaneta")
    city_key: str  # clave de `event.city`

    @property
    def label(self) -> str:
        return f"{self.name}, {self.department}"

    def as_dict(self) -> dict:
        return {"code": self.code, "name": self.name, "department": self.department,
                "label": self.label}


def _plain(text: str) -> str:
    raw = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(raw.lower().split())


@lru_cache(maxsize=1)
def _all() -> dict[str, Municipality]:
    rows = json.loads(_DATA.read_text(encoding="utf-8"))
    counts = Counter(name for _, name, _ in rows)
    out: dict[str, Municipality] = {}
    for code, name, dept in rows:
        city = _SHORT.get(code, name)
        key = normalize_city(city)
        if counts[name] > 1 and not code.endswith("001") and code not in _PREFERRED:
            key = f"{key} {_plain(dept)}"[:80]
        out[code] = Municipality(code, name, dept, city, key)
    return out


def get(code: str) -> Municipality | None:
    return _all().get((code or "").strip())


def search(query: str, limit: int = 20) -> list[Municipality]:
    """Coincidencias por inicio de palabra primero, luego por contenido; sin tildes."""
    q = _plain(query or "")
    if len(q) < 2:
        return []
    starts, contains = [], []
    for m in _all().values():
        name = _plain(m.name)
        label = _plain(m.label)
        short = _plain(m.city)
        if name.startswith(q) or short.startswith(q) or any(w.startswith(q) for w in name.split()):
            starts.append(m)
        elif q in label:
            contains.append(m)
    starts.sort(key=lambda m: (not m.code.endswith("001"), m.name))
    contains.sort(key=lambda m: m.name)
    return (starts + contains)[:limit]


def metro_core(code: str) -> Municipality | None:
    """Ciudad principal del área metropolitana (Sabaneta → Medellín), o None."""
    core = _CORE_OF.get(code)
    return get(core) if core else None


@lru_cache(maxsize=1)
def _by_key() -> dict[str, Municipality]:
    out: dict[str, Municipality] = {}
    for m in _all().values():
        out.setdefault(m.city_key, m)
    return out


def by_city_key(key: str) -> Municipality | None:
    return _by_key().get(key)


NATIONAL = "colombia"  # clave de `event.city` para festivos y puentes (feature 034)


def area_members(core_code: str) -> list[Municipality]:
    return [m for c in _METRO_CORE.get(core_code, ()) if (m := get(c))]


def area_keys(city: str | None) -> list[str]:
    """Claves de `event.city` de la zona de una propiedad (features 033 y 034).

    Su municipio, todo su área metropolitana en ambos sentidos (Sabaneta → Medellín y Medellín
    → Sabaneta, Envigado…: la DAVIarena queda en Sabaneta) y los festivos nacionales.
    `city` es el texto libre de la propiedad ("Sabaneta", "Medellín, Antioquia").
    """
    key = normalize_city(city)
    m = by_city_key(key)
    return keys_for(m) if m is not None else [key, NATIONAL]


def keys_for(m: Municipality) -> list[str]:
    keys = [m.city_key]
    core = metro_core(m.code) or (m if m.code in _METRO_CORE else None)
    if core is not None:
        for k in [core.city_key] + [x.city_key for x in area_members(core.code)]:
            if k not in keys:
                keys.append(k)
    return keys + [NATIONAL]


def area_core_key(city: str | None) -> str:
    """Clave de la ciudad principal del área (o la del propio municipio si no tiene área)."""
    key = normalize_city(city)
    m = by_city_key(key)
    core = metro_core(m.code) if m else None
    return core.city_key if core else key


def count() -> int:
    return len(_all())
