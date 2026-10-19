"""Piloto INTERNO de precios de la competencia con Apify (feature 037, issue #148).

Plan: docs/research/piloto-mercado-decodo-apify.md · Memorando legal: docs/research/legal-datos-mercado-2026-10.md

Qué hace: para una zona y varias ventanas de fechas, pide a Apify (actor público de Airbnb,
pago por anuncio) los anuncios disponibles, filtra los parecidos cerca de la propiedad
(radio y habitaciones) y calcula SOLO agregados: n, mediana, p25, p75 del precio por noche
y en qué percentil queda el precio propio.

Controles del memorando:
- Sin login, sin cuentas, sin saltar bloqueos (lo hace el proveedor con su infraestructura
  pública; aquí no se configuran desbloqueadores).
- No se guarda nada en la base de datos. A disco solo van los agregados y, para la
  verificación manual del anfitrión, como mucho 10 enlaces de anuncios por zona (públicos, sin
  nombres ni fotos), en el archivo de salida que indique quien lo corre (fuera del repo).
- Gasto acotado por corrida (`maxTotalChargeUsd`) y por número de anuncios (`maxItems`).
- El token se lee del almacén de secretos (lo pega el anfitrión en Ajustes); nunca se imprime.

Uso (desde apps/api, con el entorno de staging):
    railway run --service api-staging --environment staging \
        .venv/bin/python -m scripts.market_pilot --out /ruta/fuera/del/repo/piloto.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx

ACTOR = "tri_angle~new-fast-airbnb-scraper"
API = "https://api.apify.com/v2"


@dataclass
class Zone:
    name: str
    query: str
    lat: float
    lon: float
    radius_km: float
    min_bedrooms: int
    max_bedrooms: int
    own_price: dict[str, float] = field(default_factory=dict)  # fecha → precio propio/noche


def km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    digits = "".join(ch for ch in str(v) if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def nightly_price(item: dict, nights: int) -> float | None:
    """Precio por noche del anuncio para la estadía pedida (la forma del JSON varía)."""
    price = item.get("price") or item.get("pricing") or {}
    if isinstance(price, dict):
        total = (_num(price.get("total")) or _num((price.get("total") or {}).get("amount")
                 if isinstance(price.get("total"), dict) else None))
        per = _num(price.get("price")) or _num(price.get("amount"))
        label = str(price.get("label") or price.get("qualifier") or "").lower()
        if total:
            return total / nights
        if per:
            return per / nights if ("total" in label or "for" in label or "por" in label) else per
    return _num(price)


def coords(item: dict):
    c = item.get("coordinates") or item.get("location") or {}
    lat = _num(c.get("latitude") or c.get("lat"))
    lon = _num(c.get("longitude") or c.get("lng") or c.get("lon"))
    return (lat, lon) if lat is not None and lon is not None else (None, None)


def bedrooms(item: dict) -> int | None:
    for k in ("bedrooms", "bedroomCount", "numberOfBedrooms"):
        if item.get(k) is not None:
            return int(_num(item[k]) or 0)
    text = " ".join(str(item.get(k) or "") for k in ("subtitle", "name", "title", "structuredContent"))
    for word in text.lower().replace(",", " ").split("·"):
        w = word.strip()
        if "bedroom" in w or "habitaci" in w:
            n = _num(w.split()[0]) if w.split() else None
            if n is not None:
                return int(n)
    return None


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    return sorted_vals[f] if f == c else sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


async def run_actor(client: httpx.AsyncClient, token: str, inp: dict, *, max_items: int,
                    max_usd: float) -> tuple[list[dict], dict]:
    headers = {"Authorization": f"Bearer {token}"}
    t0 = time.monotonic()
    r = await client.post(
        f"{API}/acts/{ACTOR}/runs",
        params={"waitForFinish": 240, "maxItems": max_items, "maxTotalChargeUsd": max_usd},
        json=inp, headers=headers, timeout=300,
    )
    r.raise_for_status()
    run = r.json()["data"]
    while run.get("status") in ("READY", "RUNNING"):
        await asyncio.sleep(5)
        run = (await client.get(f"{API}/actor-runs/{run['id']}", headers=headers)).json()["data"]
    items = (await client.get(f"{API}/datasets/{run['defaultDatasetId']}/items",
                              params={"clean": 1, "format": "json"}, headers=headers,
                              timeout=120)).json()
    meta = {
        "status": run.get("status"),
        "seconds": round(time.monotonic() - t0, 1),
        "usd": run.get("usageTotalUsd"),
        "charged": run.get("chargedEventCounts"),
        "items": len(items),
    }
    return items, meta


async def pilot(zones: list[Zone], windows: list[tuple[date, date]], token: str, *,
                max_items: int, max_usd: float, sample_links: int) -> dict:
    report = {"generated": date.today().isoformat(), "actor": ACTOR, "zones": []}
    async with httpx.AsyncClient() as client:
        for z in zones:
            zr = {"zone": z.name, "query": z.query, "radius_km": z.radius_km,
                  "bedrooms": [z.min_bedrooms, z.max_bedrooms], "windows": [], "links": []}
            for ci, co in windows:
                nights = (co - ci).days
                inp = {"locationQueries": [z.query], "checkIn": ci.isoformat(),
                       "checkOut": co.isoformat(), "currency": "COP", "locale": "es-419",
                       "minBedrooms": z.min_bedrooms, "adults": 2}
                try:
                    items, meta = await run_actor(client, token, inp, max_items=max_items,
                                                  max_usd=max_usd)
                except httpx.HTTPError as exc:
                    zr["windows"].append({"check_in": ci.isoformat(), "error": type(exc).__name__})
                    continue
                prices, near, with_price, parse_fail = [], 0, 0, 0
                for it in items:
                    lat, lon = coords(it)
                    br = bedrooms(it)
                    p = nightly_price(it, nights)
                    if p is None:
                        parse_fail += 1
                        continue
                    with_price += 1
                    if lat is None or km(z.lat, z.lon, lat, lon) > z.radius_km:
                        continue
                    if br is not None and not (z.min_bedrooms <= br <= z.max_bedrooms):
                        continue
                    near += 1
                    prices.append(p)
                    if len(zr["links"]) < sample_links and it.get("url"):
                        zr["links"].append({"check_in": ci.isoformat(), "url": it["url"],
                                            "price_night": round(p)})
                prices.sort()
                own = z.own_price.get(ci.isoformat())
                pct = (sum(1 for x in prices if x <= own) / len(prices)) if (own and prices) else None
                zr["windows"].append({
                    "check_in": ci.isoformat(), "nights": nights, **meta,
                    "with_price": with_price, "parse_fail": parse_fail, "comparables": near,
                    "median": round(statistics.median(prices)) if prices else None,
                    "p25": round(percentile(prices, 0.25)) if prices else None,
                    "p75": round(percentile(prices, 0.75)) if prices else None,
                    "own_price": own, "own_percentile": round(pct * 100) if pct is not None else None,
                })
            report["zones"].append(zr)
    report["usd_total"] = round(sum((w.get("usd") or 0) for z in report["zones"]
                                    for w in z["windows"]), 4)
    return report


def default_windows(today: date) -> list[tuple[date, date]]:
    def next_wd(d: date, wd: int) -> date:
        return d + timedelta(days=(wd - d.weekday()) % 7 or 7)

    fri = next_wd(today, 4)
    tue = next_wd(fri, 1)
    return [
        (fri, fri + timedelta(days=2)),                       # próximo fin de semana
        (tue, tue + timedelta(days=2)),                       # entre semana
        (date(2026, 12, 4), date(2026, 12, 6)),               # Hebert Vargas / Garrix
        (today + timedelta(days=30), today + timedelta(days=32)),
        (today + timedelta(days=60), today + timedelta(days=62)),
        (date(2026, 11, 13), date(2026, 11, 15)),             # puente festivo
    ]


async def _own_prices(windows) -> dict[str, float]:
    """Precio propio por noche (cuenta 1, primera unidad) para comparar. Solo lectura."""
    from sqlalchemy import select

    from app.db.tenancy import tenant_session
    from app.models.property import UnitType
    from app.services import pricing_service

    out = {}
    async with tenant_session(1) as s:
        unit = (await s.execute(select(UnitType).order_by(UnitType.id))).scalars().first()
        if unit is None:
            return out
        for ci, co in windows:
            vals = [await pricing_service.get_price(s, unit.id, ci + timedelta(days=i))
                    for i in range((co - ci).days)]
            vals = [float(v) for v in vals if v]
            if vals:
                out[ci.isoformat()] = sum(vals) / len(vals)
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="archivo JSON de salida, FUERA del repo")
    ap.add_argument("--max-items", type=int, default=60)
    ap.add_argument("--max-usd", type=float, default=0.20, help="tope de gasto por corrida")
    ap.add_argument("--windows", type=int, default=6)
    ap.add_argument("--with-cartagena", action="store_true")
    args = ap.parse_args()

    from app.db.session import SessionLocal
    from app.services import secret_service

    async with SessionLocal() as s:
        await secret_service.load_cache(s)
    token = secret_service.get_secret("apify_api_token")
    if not token:
        raise SystemExit("Falta el Apify API token (Ajustes → Claves).")

    windows = default_windows(date.today())[: args.windows]
    home = Zone("Mayorca/Sabaneta (tu apartamento)", "Sabaneta, Antioquia, Colombia",
                6.159490, -75.606309, 2.0, 2, 4, await _own_prices(windows))
    zones = [home]
    if args.with_cartagena:
        zones.append(Zone("Cartagena (centro/Bocagrande)", "Cartagena, Bolívar, Colombia",
                          10.4236, -75.5512, 3.0, 2, 4))
    report = await pilot(zones, windows, token, max_items=args.max_items, max_usd=args.max_usd,
                         sample_links=10)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    for z in report["zones"]:
        print(z["zone"])
        for w in z["windows"]:
            print("  ", {k: w.get(k) for k in ("check_in", "status", "items", "with_price",
                                               "comparables", "median", "p25", "p75",
                                               "own_price", "own_percentile", "usd", "seconds")})
    print("USD total:", report["usd_total"])


if __name__ == "__main__":
    asyncio.run(main())
