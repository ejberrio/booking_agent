"""Gestión de secretos operativos (feature 017).

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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.secret import SecretChangeLog, SecretEntry

# Lista CERRADA de secretos gestionables. name == atributo de Settings (fallback env).
SECRET_NAMES: dict[str, dict[str, str]] = {
    "openai_api_key": {
        "label": "OpenAI API key",
        "service": "Agente de chat y extracción de eventos",
        "test": "llm",
    },
    "anthropic_api_key": {
        "label": "Anthropic API key",
        "service": "Agente de chat (proveedor alternativo)",
        "test": "llm",
    },
    "search_api_key": {
        "label": "Tavily API key",
        "service": "Escaneo de eventos y mercado",
        "test": "search",
    },
    "beds24_refresh_token": {
        "label": "Beds24 refresh token",
        "service": "Todo el canal (precios, reservas, disponibilidad)",
        "test": "beds24",
    },
}

_cache: dict[str, str] = {}
_unreadable: set[str] = set()


class SecretError(ValueError):
    """Datos inválidos (mensajes fijos, nunca contienen valores)."""


def _fernet() -> Fernet:
    key = urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def _hint(value: str) -> str:
    # Con valores cortos la pista revelaría una proporción grande: se omite.
    return f"…{value[-4:]}" if len(value) >= 8 else ""


def get_secret(name: str) -> str | None:
    """Valor vigente: caché (BD, cargada al arrancar y write-through) > entorno."""
    if name in _cache:
        return _cache[name]
    return getattr(settings, name, None)


async def load_cache(session: AsyncSession) -> None:
    """Carga/descifra todos los guardados. InvalidToken → ilegible + fallback env."""
    fernet = _fernet()
    _cache.clear()
    _unreadable.clear()
    rows = (await session.execute(select(SecretEntry))).scalars().all()
    for row in rows:
        try:
            _cache[row.name] = fernet.decrypt(row.value_encrypted.encode()).decode()
        except InvalidToken:
            _unreadable.add(row.name)


async def set_secret(session: AsyncSession, name: str, value: str) -> None:
    if name not in SECRET_NAMES:
        raise LookupError("Secreto no gestionable")
    clean = (value or "").strip()
    if not clean:
        raise SecretError("El valor no puede estar vacío")
    encrypted = _fernet().encrypt(clean.encode()).decode()
    hint = _hint(clean)
    existing = (
        await session.execute(select(SecretEntry).where(SecretEntry.name == name))
    ).scalar_one_or_none()
    if existing is None:
        session.add(SecretEntry(name=name, value_encrypted=encrypted, hint=hint))
    else:
        existing.value_encrypted = encrypted
        existing.hint = hint
    session.add(SecretChangeLog(name=name, action="set", hint=hint))
    await session.flush()
    _cache[name] = clean  # write-through: rotación inmediata en este proceso
    _unreadable.discard(name)


async def delete_secret(session: AsyncSession, name: str) -> None:
    if name not in SECRET_NAMES:
        raise LookupError("Secreto no gestionable")
    existing = (
        await session.execute(select(SecretEntry).where(SecretEntry.name == name))
    ).scalar_one_or_none()
    if existing is None:
        raise LookupError("No hay valor guardado en la app para este secreto")
    await session.delete(existing)
    session.add(SecretChangeLog(name=name, action="deleted"))
    await session.flush()
    _cache.pop(name, None)
    _unreadable.discard(name)


async def status(session: AsyncSession) -> list[dict]:
    """Estado enmascarado por secreto. NUNCA incluye valores (ni cifrados)."""
    rows = (await session.execute(select(SecretEntry))).scalars().all()
    stored = {r.name: r for r in rows}
    fernet = _fernet()
    out: list[dict] = []
    for name, meta in SECRET_NAMES.items():
        entry = stored.get(name)
        env_value = getattr(settings, name, None)
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


async def list_audit(session: AsyncSession, limit: int = 20) -> list[dict]:
    rows = (
        (
            await session.execute(
                select(SecretChangeLog).order_by(SecretChangeLog.changed_at.desc()).limit(limit)
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
