"""Cliente de SOLO LECTURA de la Customer API de PriceLabs (feature 041).

Endpoints (https://developers.pricelabs.co): `GET /v1/listings` y `GET /v1/neighborhood_data`.
Autenticación: cabecera `X-API-Key` (secreto `pricelabs_api_key`, nunca en logs ni en errores).
Límites: 60 peticiones/minuto y 1.000/hora por clave.

Este cliente NUNCA escribe en PriceLabs: no cambia precios, ni el origen de los datos del
vecindario, ni la sincronización. El origen (Market Dashboard + compset) se elige en PriceLabs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from app.core.config import settings
from app.services import secret_service

TIMEOUT = 120.0
FUTURE = "Future Percentile Prices"
_WANTED = {25: "25th", 50: "50th", 75: "75th", 90: "90th"}


class PriceLabsError(Exception):
    """Mensaje fijo y legible para el administrador (sin la clave ni la respuesta cruda)."""


@dataclass
class Neighborhood:
    source: str | None  # "Nearby Listings" o "Market Dashboard: <nombre>"
    currency: str | None
    categories: dict[str, int] = field(default_factory=dict)  # categoría → anuncios usados
    rows: list[list] = field(default_factory=list)  # [[fecha, p25, p50, p75, p90], …]
    category: str | None = None  # la que se usó


def api_key() -> str | None:
    return secret_service.get_secret("pricelabs_api_key")


def _error(resp: httpx.Response) -> PriceLabsError:
    code = resp.status_code
    if code in (401, 403):
        try:
            err = resp.json().get("error")
        except ValueError:
            err = None
        if code == 401 or (isinstance(err, dict) and err.get("code") == "API_KEY_INVALID"):
            return PriceLabsError(
                f"PriceLabs rechazó la clave de la API ({code}). Revisa en PriceLabs → Detalles API "
                "que la API esté activada y vuelve a copiar la clave en Ajustes."
            )
    if code == 404:
        return PriceLabsError("PriceLabs no encuentra ese anuncio en la cuenta (404).")
    if code == 429:
        return PriceLabsError("Demasiadas consultas a PriceLabs (429). Se reintenta mañana.")
    if code == 400:
        try:
            detail = str(resp.json().get("error") or "")[:120]
        except ValueError:
            detail = ""
        hint = (" PriceLabs pide tener «Sync Prices» encendido en ese anuncio."
                if "sync" in detail.lower() else "")
        return PriceLabsError(f"PriceLabs respondió 400: {detail or 'petición inválida'}.{hint}")
    return PriceLabsError(f"PriceLabs respondió {code}.")


class PriceLabsClient:
    def __init__(self, key: str | None = None, *, transport: httpx.AsyncBaseTransport | None = None):
        key = key or api_key()
        if not key:
            raise PriceLabsError("Falta la clave de la API de PriceLabs (Ajustes → Secretos).")
        self._http = httpx.AsyncClient(
            base_url=settings.pricelabs_base_url, timeout=TIMEOUT, transport=transport,
            headers={"X-API-Key": key, "Accept": "application/json"},
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            resp = await self._http.get(path, params=params)
        except httpx.HTTPError as exc:
            raise PriceLabsError(f"Sin conexión con PriceLabs ({type(exc).__name__}).") from None
        if resp.status_code != 200:
            raise _error(resp)
        try:
            return resp.json()
        except ValueError:
            raise PriceLabsError("PriceLabs devolvió una respuesta que no es JSON.") from None

    async def listings(self) -> list[dict]:
        """Anuncios de la cuenta: solo lo necesario para elegir uno (sin datos de huéspedes)."""
        data = await self._get("/v1/listings", {"skip_hidden": "true"})
        out = []
        for li in data.get("listings") or []:
            out.append({
                "id": str(li.get("id")), "pms": li.get("pms"), "name": li.get("name"),
                "city": li.get("city_name"), "bedrooms": li.get("no_of_bedrooms"),
                "sync": bool(li.get("push_enabled")),
            })
        return out

    async def neighborhood(self, listing_id: str, pms: str, bedrooms: int = 0) -> Neighborhood:
        data = await self._get("/v1/neighborhood_data", {"listing_id": listing_id, "pms": pms})
        return parse_neighborhood(data.get("data") or {}, bedrooms)


def _label_index(labels: list[str]) -> dict[int, int]:
    idx: dict[int, int] = {}
    for i, label in enumerate(labels):
        for p, tag in _WANTED.items():
            if label.lower().startswith(tag) and "percentile" in label.lower():
                idx.setdefault(p, i)
    return idx


def pick_category(categories: dict, bedrooms: int) -> str | None:
    """La categoría del tamaño pedido ("3"); si solo hay una (compset del Market Dashboard),
    esa; con "todas" (0 en StayLever), "All" si existe."""
    if not categories:
        return None
    if bedrooms and str(bedrooms) in categories:
        return str(bedrooms)
    if len(categories) == 1:
        return next(iter(categories))
    if not bedrooms and "All" in categories:
        return "All"
    return None


def parse_neighborhood(data: dict, bedrooms: int = 0) -> Neighborhood:
    future = data.get(FUTURE) or {}
    cats = future.get("Category") or {}
    nb = Neighborhood(
        source=data.get("Neighborhood Data Source"), currency=data.get("currency"),
        categories={str(k): int(v.get("Listings Used") or 0) for k, v in cats.items()},
    )
    idx = _label_index(future.get("Labels") or [])
    if len(idx) < 4:
        raise PriceLabsError("La respuesta de PriceLabs no trae los percentiles 25/50/75/90.")
    cat = pick_category(cats, bedrooms)
    if cat is None:
        raise PriceLabsError(
            f"No hay datos para {bedrooms} habitaciones; categorías disponibles: "
            f"{', '.join(nb.categories) or 'ninguna'}."
        )
    nb.category = cat
    block = cats[cat]
    xs, ys = block.get("X_values") or [], block.get("Y_values") or []
    for j, day in enumerate(xs):
        try:
            vals = [ys[idx[p]][j] for p in (25, 50, 75, 90)]
        except (IndexError, TypeError):
            continue
        if any(not isinstance(v, (int, float)) or v <= 0 for v in vals) or vals != sorted(vals):
            continue
        nb.rows.append([str(day)[:10], *[float(v) for v in vals]])
    return nb
