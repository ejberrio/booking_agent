"""Adaptador Firebase Cloud Messaging (HTTP v1) — feature 025.

Autenticación con la cuenta de servicio (JSON guardado como secreto cifrado):
JWT RS256 firmado con `cryptography` → token OAuth (caché ~55 min) → messages:send.
Sin dependencias nuevas. Nunca registra el token del teléfono ni la credencial.
"""

from __future__ import annotations

import base64
import json
import time

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.push.base import PushMessage, PushResult

SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"
CHANNEL_ID = "staylever"


class FcmConfigError(ValueError):
    """Credencial ausente o con formato inválido (mensaje fijo, sin valores)."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def parse_service_account(raw: str | None) -> dict:
    if not raw:
        raise FcmConfigError("credencial de avisos sin configurar")
    try:
        info = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise FcmConfigError("la credencial de avisos no es un JSON válido") from exc
    for key in ("project_id", "client_email", "private_key"):
        if not info.get(key):
            raise FcmConfigError("a la credencial de avisos le falta " + key)
    return info


def signed_assertion(info: dict, now: int) -> str:
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": info["client_email"],
        "scope": SCOPE,
        "aud": info.get("token_uri") or DEFAULT_TOKEN_URI,
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = f"{_b64(json.dumps(header).encode())}.{_b64(json.dumps(claims).encode())}"
    key = serialization.load_pem_private_key(info["private_key"].encode(), password=None)
    signature = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{_b64(signature)}"


class FcmSender:
    def __init__(self, service_account_json: str | None, client: httpx.AsyncClient | None = None):
        self.info = parse_service_account(service_account_json)
        self._client = client or httpx.AsyncClient(timeout=15)
        self._owns_client = client is None
        self._token: str | None = None
        self._token_exp = 0.0

    async def _access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_exp - 300:
            return self._token
        resp = await self._client.post(
            self.info.get("token_uri") or DEFAULT_TOKEN_URI,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_assertion(self.info, int(now)),
            },
        )
        if resp.status_code != 200:
            raise FcmConfigError(f"Firebase rechazó la credencial de avisos ({resp.status_code})")
        body = resp.json()
        self._token = body["access_token"]
        self._token_exp = now + float(body.get("expires_in", 3600))
        return self._token

    async def check(self) -> None:
        """Prueba de la credencial (Ajustes → Probar): obtener un token OAuth."""
        await self._access_token()

    async def send(self, message: PushMessage) -> PushResult:
        try:
            token = await self._access_token()
        except FcmConfigError as exc:
            return PushResult("error", str(exc))
        payload = {
            "message": {
                "token": message.token,
                "notification": {"title": message.title, "body": message.body},
                "data": message.data,
                "android": {"priority": "high", "notification": {"channel_id": CHANNEL_ID}},
            }
        }
        url = f"https://fcm.googleapis.com/v1/projects/{self.info['project_id']}/messages:send"
        try:
            resp = await self._client.post(
                url, json=payload, headers={"Authorization": f"Bearer {token}"}
            )
        except httpx.HTTPError as exc:
            return PushResult("error", f"sin respuesta de Firebase ({type(exc).__name__})")
        if resp.status_code == 200:
            return PushResult("ok")
        text = resp.text
        if resp.status_code == 404 or "UNREGISTERED" in text or (
            resp.status_code == 400 and "registration token" in text.lower()
        ):
            return PushResult("invalid_token", "el teléfono ya no está registrado")
        return PushResult("error", f"Firebase respondió {resp.status_code}")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
