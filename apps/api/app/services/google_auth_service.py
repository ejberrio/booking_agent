"""Entrar con Google (feature 026, entrega 4).

Flujo de código con PKCE y estado guardado en el servidor (research D7):

1. `start` guarda un `auth_token` de propósito `oauth_state` (vence en 10 min) con el verificador
   PKCE, el modo, la invitación y el cliente (web o app), y devuelve la URL de Google.
2. `callback` consume ese estado, canjea el código en el endpoint de tokens de Google (por TLS,
   con el secreto del cliente) y lee `sub`, `email`, `email_verified` y `name` del `id_token`.
   Busca al usuario por `google_sub`; si no, por correo **verificado por Google** (y lo vincula);
   si no existe, crea la cuenta (con invitación mientras el registro esté cerrado).
3. En la web devuelve una sesión. En la app de Android (Google no permite entrar dentro de un
   WebView) devuelve un **código de traspaso** de 2 minutos ligado al `challenge` S256 que mandó
   la app; la app lo cambia por su sesión en `handoff` presentando el verificador.

Las credenciales son secretos de plataforma (`google_oauth_client_id/secret`).
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets as pysecrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import digest, new_token, normalize_email
from app.core.config import settings
from app.models.account import Account, AccountStatus
from app.models.auth import AppUser, AuthToken, Membership
from app.models.mixins import _now
from app.services.auth_service import (
    LANGS,
    AuthError,
    _aware,
    _membership,
    _user_by_email,
    accept_terms,
    create_session,
)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")
STATE_TTL = timedelta(minutes=10)
HANDOFF_TTL = timedelta(minutes=2)

_INVALID = "El inicio de sesión con Google venció o no es válido. Inténtalo de nuevo."


def credentials() -> tuple[str, str] | None:
    from app.services.secret_service import get_secret

    cid = get_secret("google_oauth_client_id")
    secret = get_secret("google_oauth_client_secret")
    return (cid.strip(), secret.strip()) if cid and secret else None


def is_configured() -> bool:
    return credentials() is not None


def redirect_uri() -> str:
    return f"{settings.public_base_url.rstrip('/')}/api/auth/google/callback"


def s256(value: str) -> str:
    raw = hashlib.sha256(value.encode()).digest()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _valid_challenge(challenge: str | None) -> bool:
    return bool(challenge) and 43 <= len(challenge) <= 128 and all(
        c.isalnum() or c in "-_" for c in challenge
    )


async def start(
    session: AsyncSession,
    *,
    mode: str = "login",
    client: str = "web",
    invite_code: str | None = None,
    challenge: str | None = None,
    language: str = "es",
    accept: bool = False,
) -> str:
    creds = credentials()
    if creds is None:
        raise AuthError("google_unavailable", "Entrar con Google no está disponible por ahora", 503)
    if client == "app" and not _valid_challenge(challenge):
        raise AuthError("invalid_data", _INVALID, 400)
    state = new_token()
    verifier = pysecrets.token_urlsafe(48)
    session.add(
        AuthToken(
            purpose="oauth_state",
            token_hash=digest(state),
            payload={
                "verifier": verifier,
                "mode": "register" if mode == "register" else "login",
                "client": "app" if client == "app" else "web",
                "invite": (invite_code or "").strip()[:40] or None,
                "challenge": challenge if client == "app" else None,
                "language": language if language in LANGS else "es",
                "accept": bool(accept),
            },
            expires_at=_now() + STATE_TTL,
        )
    )
    await session.commit()
    query = {
        "client_id": creds[0],
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": s256(verifier),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{AUTH_URL}?{urlencode(query)}"


@dataclass
class GoogleProfile:
    sub: str
    email: str
    email_verified: bool
    name: str


def _decode_id_token(id_token: str, client_id: str) -> GoogleProfile:
    """Lee el id_token recibido directamente de Google por TLS (no hace falta verificar la
    firma en este canal, según la documentación de Google), pero sí emisor, audiencia y vigencia."""
    try:
        payload = id_token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        raise AuthError("google_failed", _INVALID, 400) from None
    aud = claims.get("aud")
    auds = aud if isinstance(aud, list) else [aud]
    if (
        claims.get("iss") not in ISSUERS
        or client_id not in auds
        or float(claims.get("exp", 0)) < time.time()
        or not claims.get("sub")
        or not claims.get("email")
    ):
        raise AuthError("google_failed", _INVALID, 400)
    verified = claims.get("email_verified")
    return GoogleProfile(
        sub=str(claims["sub"]),
        email=normalize_email(str(claims["email"])),
        email_verified=verified is True or verified == "true",
        name=str(claims.get("name") or claims["email"]).strip()[:120],
    )


async def _exchange(
    code: str, verifier: str, creds: tuple[str, str], transport: httpx.AsyncBaseTransport | None
) -> GoogleProfile:
    data = {
        "code": code,
        "client_id": creds[0],
        "client_secret": creds[1],
        "redirect_uri": redirect_uri(),
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }
    try:
        async with httpx.AsyncClient(timeout=15, transport=transport) as c:
            r = await c.post(TOKEN_URL, data=data)
    except httpx.HTTPError:
        raise AuthError("google_failed", "No pudimos hablar con Google. Inténtalo de nuevo.", 502) from None
    if r.status_code != 200 or "id_token" not in r.json():
        raise AuthError("google_failed", _INVALID, 400)
    return _decode_id_token(r.json()["id_token"], creds[0])


async def _take_state(session: AsyncSession, state: str) -> dict:
    row = (
        await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == digest(state or ""), AuthToken.purpose == "oauth_state"
            )
        )
    ).scalar_one_or_none()
    if row is None or row.used_at is not None or _aware(row.expires_at) <= _now():
        raise AuthError("google_state", _INVALID, 400)
    row.used_at = _now()
    await session.flush()
    return dict(row.payload or {})


async def _find_or_create(session: AsyncSession, profile: GoogleProfile, st: dict) -> AppUser:
    from app.services import invite_service

    user = (
        await session.execute(select(AppUser).where(AppUser.google_sub == profile.sub))
    ).scalar_one_or_none()
    if user is not None:
        return user
    by_email = await _user_by_email(session, profile.email)
    if by_email is not None:
        # Solo se vincula con un correo que Google confirma: si no, alguien podría crear una
        # cuenta de Google con el correo de otra persona y entrar a la suya.
        if not profile.email_verified:
            raise AuthError(
                "google_unverified",
                "Tu correo de Google no está verificado. Entra con tu correo y contraseña.",
                403,
            )
        if by_email.google_sub and by_email.google_sub != profile.sub:
            raise AuthError("google_failed", _INVALID, 400)
        by_email.google_sub = profile.sub
        if by_email.email_verified_at is None:
            by_email.email_verified_at = _now()
        return by_email
    if not profile.email_verified:
        raise AuthError(
            "google_unverified", "Tu correo de Google no está verificado.", 403
        )
    invite = None
    if not await invite_service.registration_open(session):
        invite = await invite_service.find_valid(session, st.get("invite") or "")
        if invite is None:
            code = "invite_required" if not st.get("invite") else "invite_invalid"
            raise AuthError(
                code,
                "StayLever está en beta por invitación"
                if code == "invite_required"
                else "El código de invitación no es válido, venció o ya se usó",
                400,
            )
    account = Account(name=profile.name or profile.email)
    session.add(account)
    await session.flush()
    if invite is not None and not await invite_service.consume(session, invite, account.id):
        raise AuthError("invite_invalid", "El código de invitación no es válido, venció o ya se usó", 400)
    user = AppUser(
        email=profile.email,
        name=profile.name or profile.email,
        password_hash=None,
        google_sub=profile.sub,
        email_verified_at=_now(),
        language=st.get("language") or "es",
    )
    session.add(user)
    await session.flush()
    session.add(Membership(user_id=user.id, account_id=account.id, role="owner"))
    await session.flush()
    return user


@dataclass
class CallbackResult:
    client: str
    token: str | None = None
    expires: datetime | None = None
    handoff_code: str | None = None


async def callback(
    session: AsyncSession,
    *,
    code: str,
    state: str,
    user_agent: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> CallbackResult:
    creds = credentials()
    if creds is None:
        raise AuthError("google_unavailable", "Entrar con Google no está disponible por ahora", 503)
    st = await _take_state(session, state)
    await session.commit()  # el estado sirve una sola vez, aunque lo que sigue falle
    profile = await _exchange(code, st.get("verifier", ""), creds, transport)
    try:
        user = await _find_or_create(session, profile, st)
        member = await _membership(session, user.id)
        account = await session.get(Account, member.account_id) if member else None
        if account is None or account.status != AccountStatus.active:
            raise AuthError("disabled", "Esta cuenta está desactivada", 403)
    except AuthError:
        await session.rollback()
        raise
    user.last_login_at = _now()
    if st.get("accept"):  # casilla marcada antes de ir a Google (feature 028)
        await accept_terms(session, user.id)
    if st.get("client") == "app":
        handoff = new_token()
        session.add(
            AuthToken(
                purpose="app_handoff",
                token_hash=digest(handoff),
                user_id=user.id,
                payload={"challenge": st.get("challenge")},
                expires_at=_now() + HANDOFF_TTL,
            )
        )
        await session.commit()
        return CallbackResult(client="app", handoff_code=handoff)
    token, expires = await create_session(session, user, "web", user_agent)
    await session.commit()
    return CallbackResult(client="web", token=token, expires=expires)


async def handoff(
    session: AsyncSession, *, code: str, verifier: str, user_agent: str | None = None
) -> tuple[str, datetime, AppUser]:
    """La app cambia el código de traspaso por su sesión de 90 días (un solo uso, 2 min)."""
    row = (
        await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == digest(code or ""), AuthToken.purpose == "app_handoff"
            )
        )
    ).scalar_one_or_none()
    if row is None or row.used_at is not None or _aware(row.expires_at) <= _now():
        raise AuthError("google_state", _INVALID, 400)
    row.used_at = _now()  # un intento fallido también lo gasta
    challenge = (row.payload or {}).get("challenge")
    if not challenge or not pysecrets.compare_digest(s256(verifier or ""), challenge):
        await session.commit()
        raise AuthError("google_state", _INVALID, 400)
    user = await session.get(AppUser, row.user_id)
    member = await _membership(session, user.id) if user else None
    account = await session.get(Account, member.account_id) if member else None
    if user is None or account is None or account.status != AccountStatus.active:
        await session.commit()
        raise AuthError("disabled", "Esta cuenta está desactivada", 403)
    token, expires = await create_session(session, user, "app", user_agent)
    await session.commit()
    return token, expires, user
