"""Feature 017: cifrado, precedencia y auditoría de secretos (núcleo)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.secret import SecretChangeLog, SecretEntry
from app.services import secret_service as svc
from app.services.secret_service import SecretError

pytestmark = pytest.mark.anyio

SENTINEL = "SENTINEL-XYZ-1234"


@pytest.fixture(autouse=True)
def _clean_cache():
    # La caché es estado de módulo: limpiar entre tests.
    svc._cache.clear()
    svc._unreadable.clear()
    yield
    svc._cache.clear()
    svc._unreadable.clear()


async def test_roundtrip_y_write_through(session):
    await svc.set_secret(session, "search_api_key", f"  {SENTINEL}  ")  # recorta espacios
    # write-through: sin recargar, get_secret ya devuelve el nuevo
    assert svc.get_secret("search_api_key") == SENTINEL
    # en BD está cifrado (no en claro)
    row = (await session.execute(select(SecretEntry))).scalar_one()
    assert SENTINEL not in row.value_encrypted
    assert row.hint == "…1234"
    # recarga desde BD (nuevo proceso) → descifra bien
    svc._cache.clear()
    await svc.load_cache(session)
    assert svc.get_secret("search_api_key") == SENTINEL


async def test_precedencia_bd_env_none(session, monkeypatch):
    monkeypatch.setattr(settings, "search_api_key", "env-value-xyz")
    assert svc.get_secret("search_api_key") == "env-value-xyz"  # sin BD → env
    await svc.set_secret(session, "search_api_key", "db-value-abcd")
    assert svc.get_secret("search_api_key") == "db-value-abcd"  # BD gana
    await svc.delete_secret(session, "search_api_key")
    assert svc.get_secret("search_api_key") == "env-value-xyz"  # DELETE → env
    monkeypatch.setattr(settings, "search_api_key", None)
    assert svc.get_secret("search_api_key") is None  # FR-012: sin nada → None


async def test_clave_rotada_ilegible_y_fallback(session, monkeypatch):
    await svc.set_secret(session, "openai_api_key", "sk-old-value-123")
    monkeypatch.setattr(settings, "secret_key", "OTRA-clave-distinta")
    monkeypatch.setattr(settings, "openai_api_key", "sk-env-fallback")
    # load_cache no lanza; marca ilegible y cae al entorno
    svc._cache.clear()
    await svc.load_cache(session)
    assert (None, "openai_api_key") in svc._unreadable
    assert svc.get_secret("openai_api_key") == "sk-env-fallback"
    st = {s["name"]: s for s in await svc.status(session)}
    assert st["openai_api_key"]["unreadable"] is True
    assert st["openai_api_key"]["source"] == "env"
    # guardar de nuevo repara
    await svc.set_secret(session, "openai_api_key", "sk-new-value-456")
    assert svc.get_secret("openai_api_key") == "sk-new-value-456"


async def test_hint_valor_corto_vacio(session):
    await svc.set_secret(session, "search_api_key", "abc1234")  # 7 chars
    row = (await session.execute(select(SecretEntry))).scalar_one()
    assert row.hint == ""


async def test_validaciones(session):
    with pytest.raises(SecretError):
        await svc.set_secret(session, "search_api_key", "   ")
    with pytest.raises(LookupError):
        await svc.set_secret(session, "no_es_un_secreto", "x" * 20)
    with pytest.raises(LookupError):
        await svc.delete_secret(session, "search_api_key")  # nada guardado


async def test_auditoria_sin_valores(session):
    await svc.set_secret(session, "beds24_refresh_token", SENTINEL)
    await svc.delete_secret(session, "beds24_refresh_token")
    logs = (await session.execute(select(SecretChangeLog))).scalars().all()
    assert [(entry.action, entry.hint) for entry in logs] == [("set", "…1234"), ("deleted", "")]
    audit = await svc.list_audit(session)
    assert all(SENTINEL not in str(e) for e in audit)


async def test_status_enmascarado(session, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-por-entorno-9999")
    await svc.set_secret(session, "search_api_key", SENTINEL)
    st = {s["name"]: s for s in await svc.status(session)}
    assert st["openai_api_key"]["source"] == "env"
    assert st["openai_api_key"]["hint"] == "…9999"
    assert st["search_api_key"]["source"] == "app"
    assert st["search_api_key"]["hint"] == "…1234"
    assert st["anthropic_api_key"]["configured"] in (False, True)  # según entorno de test
    assert SENTINEL not in str(st)  # nunca el valor
