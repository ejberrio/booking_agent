"""Gestión de secretos operativos (features 017 y 026).

Feature 026: cada secreto es **de plataforma** (claves de IA, búsqueda, avisos, correo,
Google: los paga/administra el host para todos) o **de una cuenta** (Beds24). La caché
va por (cuenta | None, nombre); el fallback a variables de entorno solo aplica a los de
plataforma y, por compatibilidad, a los de la cuenta nº 1.

Cifrado Fernet en reposo (clave derivada de SECRET_KEY) + caché en memoria del
proceso con precedencia BD > variable de entorno. Write-only: los valores nunca
salen de este módulo hacia respuestas, logs ni auditoría (solo la pista de los
últimos 4 caracteres). `get_secret` es SÍNCRONO para poder usarse en
constructores/funciones sync (p. ej. get_adapter).
"""

from __future__ import annotations

import hashlib
from base64 import urlsafe_b64encode

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.tenancy import TenantContextMissing, current_account_id
from app.models.account import FIRST_ACCOUNT_ID
from app.models.secret import SecretChangeLog, SecretEntry

# Lista CERRADA de secretos gestionables. name == atributo de Settings (fallback env).
SECRET_NAMES: dict[str, dict[str, str]] = {
    "openai_api_key": {
        "scope": "platform",
        "label": "OpenAI API key",
        "service": "Agente de chat y extracción de eventos",
        "test": "llm",
    },
    "anthropic_api_key": {
        "scope": "platform",
        "label": "Anthropic API key",
        "service": "Agente de chat (proveedor alternativo)",
        "test": "llm",
    },
    "search_api_key": {
        "scope": "platform",
        "label": "Tavily API key",
        "service": "Escaneo de eventos y mercado",
        "test": "search",
    },
    "beds24_refresh_token": {
        "scope": "account",
        "label": "Beds24 refresh token",
        "service": "Todo el canal (precios, reservas, disponibilidad)",
        "test": "beds24",
    },
    # Feature 020: la genera la app (Ajustes → Avisos en tiempo real) y se pega en
    # Beds24 como Custom Header. Sin variable de entorno: ausente = avisos apagados.
    "beds24_webhook_key": {
        "scope": "account",
        "label": "Clave de avisos de Beds24",
        "service": "Reservas en tiempo real (avisos de Beds24)",
        "test": "webhook",
    },
    # Feature 025: cuenta de servicio de Firebase (JSON) para avisos al celular.
    "fcm_service_account": {
        "scope": "platform",
        "label": "Credencial de avisos (Firebase)",
        "service": "Avisos al celular (app de Android/iPhone)",
        "test": "push",
    },
    # Feature 026: correo transaccional (Resend) para verificación y recuperación.
    "email_api_key": {
        "scope": "platform",
        "label": "Correo (Resend API key)",
        "service": "Correos de verificación y recuperación de contraseña",
        "test": "none",
    },
    # Feature 026: "Entrar con Google" (cliente OAuth tipo "Aplicación web").
    "google_oauth_client_id": {
        "scope": "platform",
        "label": "Google OAuth — ID de cliente",
        "service": "Entrar con Google",
        "test": "none",
    },
    "google_oauth_client_secret": {
        "scope": "platform",
        "label": "Google OAuth — secreto de cliente",
        "service": "Entrar con Google",
        "test": "none",
    },
}

PLATFORM = "platform"
ACCOUNT = "account"

_cache: dict[tuple[int | None, str], str] = {}
_unreadable: set[tuple[int | None, str]] = set()


class SecretError(ValueError):
    """Datos inválidos (mensajes fijos, nunca contienen valores)."""


def scope_of(name: str) -> str:
    meta = SECRET_NAMES.get(name)
    if meta is None:
        raise LookupError("Secreto no gestionable")
    return meta["scope"]


def _fernet() -> Fernet:
    key = urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def _hint(value: str) -> str:
    # Con valores cortos la pista revelaría una proporción grande: se omite.
    return f"…{value[-4:]}" if len(value) >= 8 else ""


def _env(name: str, account_id: int | None) -> str | None:
    # Entorno: plataforma siempre; de cuenta solo la nº 1 (compatibilidad, feature 026).
    if account_id is None or account_id == FIRST_ACCOUNT_ID:
        return getattr(settings, name, None)
    return None


def get_secret(name: str, account_id: int | None = None) -> str | None:
    """Valor vigente: caché (BD, cargada al arrancar y write-through) > entorno.

    Los de cuenta exigen `account_id` (nunca se resuelven "por defecto").
    """
    if scope_of(name) == PLATFORM:
        account_id = None
    elif account_id is None:
        raise TenantContextMissing(f"el secreto {name} es de una cuenta")
    key = (account_id, name)
    if key in _cache:
        return _cache[key]
    return _env(name, account_id)


def accounts_with(name: str) -> list[tuple[int, str]]:
    """(cuenta, valor) de un secreto de cuenta guardado (p. ej. claves de webhook)."""
    return [(acc, v) for (acc, n), v in _cache.items() if n == name and acc is not None]


def _target_account(session: AsyncSession, name: str) -> int | None:
    if scope_of(name) == PLATFORM:
        return None
    account_id = current_account_id(session)
    if account_id is None:
        raise TenantContextMissing(f"el secreto {name} es de una cuenta")
    return account_id


def _where(account_id: int | None, name: str):
    cond = SecretEntry.account_id.is_(None) if account_id is None else (
        SecretEntry.account_id == account_id
    )
    return select(SecretEntry).where(cond, SecretEntry.name == name)


async def load_cache(session: AsyncSession) -> None:
    """Carga/descifra todos los guardados. InvalidToken → ilegible + fallback env."""
    fernet = _fernet()
    _cache.clear()
    _unreadable.clear()
    rows = (await session.execute(select(SecretEntry))).scalars().all()
    for row in rows:
        key = (row.account_id, row.name)
        try:
            _cache[key] = fernet.decrypt(row.value_encrypted.encode()).decode()
        except InvalidToken:
            _unreadable.add(key)


async def set_secret(session: AsyncSession, name: str, value: str) -> None:
    """Guarda un secreto en su ámbito: plataforma, o la cuenta de la sesión."""
    account_id = _target_account(session, name)
    clean = (value or "").strip()
    if not clean:
        raise SecretError("El valor no puede estar vacío")
    encrypted = _fernet().encrypt(clean.encode()).decode()
    hint = _hint(clean)
    existing = (await session.execute(_where(account_id, name))).scalar_one_or_none()
    if existing is None:
        session.add(
            SecretEntry(account_id=account_id, name=name, value_encrypted=encrypted, hint=hint)
        )
    else:
        existing.value_encrypted = encrypted
        existing.hint = hint
    session.add(SecretChangeLog(account_id=account_id, name=name, action="set", hint=hint))
    await session.flush()
    _cache[(account_id, name)] = clean  # write-through: rotación inmediata en este proceso
    _unreadable.discard((account_id, name))


async def delete_secret(session: AsyncSession, name: str) -> None:
    account_id = _target_account(session, name)
    existing = (await session.execute(_where(account_id, name))).scalar_one_or_none()
    if existing is None:
        raise LookupError("No hay valor guardado en la app para este secreto")
    await session.delete(existing)
    session.add(SecretChangeLog(account_id=account_id, name=name, action="deleted"))
    await session.flush()
    _cache.pop((account_id, name), None)
    _unreadable.discard((account_id, name))


async def status(session: AsyncSession, *, include_platform: bool = True) -> list[dict]:
    """Estado enmascarado de los secretos visibles. NUNCA incluye valores (ni cifrados).

    De cuenta: los de la cuenta de la sesión. De plataforma: solo si `include_platform`
    (administrador de plataforma).
    """
    account_id = current_account_id(session)
    fernet = _fernet()
    out: list[dict] = []
    for name, meta in SECRET_NAMES.items():
        scope = meta["scope"]
        if scope == PLATFORM and not include_platform:
            continue
        if scope == ACCOUNT and account_id is None:
            continue
        owner = None if scope == PLATFORM else account_id
        entry = (await session.execute(_where(owner, name))).scalar_one_or_none()
        env_value = _env(name, owner)
        unreadable = False
        if entry is not None:
            try:
                fernet.decrypt(entry.value_encrypted.encode())  # el valor se descarta
            except InvalidToken:
                unreadable = True
        if entry is not None and not unreadable:
            source, hint = "app", entry.hint
        elif env_value:
            source, hint = "env", _hint(env_value)
        else:
            source, hint = None, ""
        out.append(
            {
                "name": name,
                "scope": scope,
                "label": meta["label"],
                "service": meta["service"],
                "configured": source is not None,
                "source": source,
                "hint": hint,
                "updated_at": entry.updated_at.isoformat() if entry is not None else None,
                "unreadable": entry is not None and unreadable,
            }
        )
    return out


async def list_audit(
    session: AsyncSession, limit: int = 20, *, include_platform: bool = True
) -> list[dict]:
    account_id = current_account_id(session)
    conds = []
    if account_id is not None:
        conds.append(SecretChangeLog.account_id == account_id)
    if include_platform:
        conds.append(SecretChangeLog.account_id.is_(None))
    if not conds:
        return []
    rows = (
        (
            await session.execute(
                select(SecretChangeLog)
                .where(or_(*conds))
                .order_by(SecretChangeLog.changed_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "name": r.name,
            "action": r.action,
            "hint": r.hint,
            "changed_at": r.changed_at.isoformat(),
        }
        for r in rows
    ]
