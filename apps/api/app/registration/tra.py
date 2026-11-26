"""Cliente de la API para PMS de la TRA del MinCIT (Res. 409 de 2022). Feature 046.

- `POST {base}/one/`  huésped principal → `{"code": N}`
- `POST {base}/two/`  cada acompañante con `padre = N` → `{"code": M}`
- Autenticación `Authorization: token <token del RNT>`. No hay ambiente de pruebas ni
  operaciones para corregir o anular.

Los errores NUNCA llevan el cuerpo enviado ni la respuesta completa (pueden tener datos
personales): solo el estado HTTP y, si el MinCIT los nombra, los campos rechazados.
"""

from __future__ import annotations

import itertools

import httpx

BASE_URL = "https://pms.mincit.gov.co"


class TraError(Exception):
    """Mensaje legible para el anfitrión, sin datos personales."""


class TraAuthError(TraError):
    pass


class TraUnavailable(TraError):
    pass


def _fields(body) -> list[str]:
    """Nombres de campos que el MinCIT señala (p. ej. {"numero_identificacion": ["…"]})."""
    if isinstance(body, dict):
        return sorted(k for k in body if k not in ("detail", "code"))[:6]
    return []


class TraClient:
    def __init__(self, token: str, base_url: str = BASE_URL, timeout: float = 20.0):
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout,
            headers={"Authorization": f"token {token}", "Accept": "application/json"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, payload: dict) -> int:
        try:
            r = await self._client.post(path, json=payload)
        except httpx.HTTPError:
            raise TraUnavailable("El MinCIT no respondió. Intenta en unos minutos.") from None
        if r.status_code in (401, 403):
            raise TraAuthError("El MinCIT rechazó el token: revisa el token de tu RNT en Ajustes.")
        if r.status_code >= 500:
            raise TraUnavailable(f"El MinCIT respondió con un error ({r.status_code}). Intenta más tarde.")
        try:
            body = r.json()
        except ValueError:
            body = None
        if r.status_code >= 400:
            fields = _fields(body)
            extra = f": revisa {', '.join(fields)}" if fields else ""
            raise TraError(f"El MinCIT rechazó los datos ({r.status_code}){extra}.")
        code = body.get("code") if isinstance(body, dict) else None
        if not isinstance(code, int):
            raise TraError("El MinCIT respondió sin código de registro.")
        return code

    async def send_main(self, payload: dict) -> int:
        return await self._post("/one/", payload)

    async def send_companion(self, payload: dict) -> int:
        return await self._post("/two/", payload)


class SimulatedTraClient:
    """Ambiente de pruebas (staging): no llama al MinCIT, devuelve códigos falsos."""

    _seq = itertools.count(1000)

    def __init__(self, *_, **__):
        self.sent: list[tuple[str, dict]] = []

    async def aclose(self) -> None:
        return None

    async def send_main(self, payload: dict) -> int:
        self.sent.append(("one", payload))
        return next(self._seq)

    async def send_companion(self, payload: dict) -> int:
        self.sent.append(("two", payload))
        return next(self._seq)
