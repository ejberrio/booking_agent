"""Gestión write-only de secretos (feature 017). NINGUNA respuesta contiene valores.

Los mensajes de error son FIJOS (nunca interpolan valores ni excepciones crudas).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services import secret_service
from app.services.secret_service import SECRET_NAMES, SecretError, get_secret

router = APIRouter()


class SecretValueRequest(BaseModel):
    value: str


async def _one_status(session: AsyncSession, name: str) -> dict:
    for s in await secret_service.status(session):
        if s["name"] == name:
            return s
    raise HTTPException(status_code=404, detail="Secreto no gestionable")


@router.get("")
async def list_secrets(session: AsyncSession = Depends(get_session)):
    return {"secrets": await secret_service.status(session)}


@router.get("/audit")
async def audit(session: AsyncSession = Depends(get_session)):
    return {"entries": await secret_service.list_audit(session)}


@router.put("/{name}")
async def set_secret(
    name: str, req: SecretValueRequest, session: AsyncSession = Depends(get_session)
):
    try:
        await secret_service.set_secret(session, name, req.value)
        await session.commit()
        return await _one_status(session, name)
    except LookupError:
        raise HTTPException(status_code=404, detail="Secreto no gestionable") from None
    except SecretError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


class InviteCodeRequest(BaseModel):
    code: str


@router.post("/beds24_refresh_token/invite")
async def redeem_beds24_invite(
    req: InviteCodeRequest, session: AsyncSession = Depends(get_session)
):
    """Canjea un código de invitación de Beds24 y guarda el refresh token resultante.

    El host solo pega el código (Beds24 → Settings → Marketplace → API → Generate invite code);
    el token nunca sale del servidor.
    """
    from app.channels.beds24_v2 import exchange_invite_code
    from app.channels.errors import AuthError, ChannelError
    from app.core.config import settings

    if not req.code.strip():
        raise HTTPException(status_code=422, detail="El código no puede estar vacío")
    try:
        token = await exchange_invite_code(req.code, base_url=settings.beds24_v2_base_url)
    except AuthError:
        raise HTTPException(
            status_code=422,
            detail="Beds24 rechazó el código (¿vencido o ya usado?). Genera uno nuevo.",
        ) from None
    except ChannelError:
        raise HTTPException(status_code=503, detail=_UNAVAILABLE) from None
    await secret_service.set_secret(session, "beds24_refresh_token", token)
    await session.commit()
    return await _one_status(session, "beds24_refresh_token")


@router.delete("/{name}")
async def delete_secret(name: str, session: AsyncSession = Depends(get_session)):
    try:
        await secret_service.delete_secret(session, name)
        await session.commit()
        return await _one_status(session, name)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


# --------- probar por servicio (solo lectura; detail categorizado y FIJO) ---------

_OK = "conexión OK"
_BAD_CREDENTIAL = "credencial rechazada por el proveedor"
_UNAVAILABLE = "servicio no disponible o error de red"


async def _test_llm(name: str) -> dict:
    api_key = get_secret(name)
    if not api_key:
        return {"ok": False, "detail": "sin credencial configurada"}
    import litellm

    # Petición mínima con un modelo barato del proveedor correspondiente.
    model = (
        "anthropic/claude-haiku-4-5-20251001"
        if name == "anthropic_api_key"
        else "openai/gpt-4o-mini"
    )
    try:
        await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            api_key=api_key,
        )
        return {"ok": True, "detail": _OK}
    except Exception as exc:  # mensajes categorizados, jamás la excepción cruda
        text = type(exc).__name__.lower()
        if "auth" in text or "permission" in text:
            return {"ok": False, "detail": _BAD_CREDENTIAL}
        return {"ok": False, "detail": _UNAVAILABLE}


async def _test_search() -> dict:
    from app.search.tavily import TavilyProvider

    api_key = get_secret("search_api_key")
    if not api_key:
        return {"ok": False, "detail": "sin credencial configurada"}
    provider = TavilyProvider(api_key=api_key)
    try:
        results = await provider.search("ping", max_results=1)
        if results:
            return {"ok": True, "detail": _OK}
        return {"ok": False, "detail": _BAD_CREDENTIAL}
    except Exception:
        return {"ok": False, "detail": _UNAVAILABLE}
    finally:
        await provider.aclose()


async def _test_beds24() -> dict:
    from app.api.routes.sync import get_adapter
    from app.channels.errors import AuthError

    adapter = get_adapter()
    try:
        info = await adapter.test_connection()
        if info.ok:
            n = len(info.properties or [])
            return {"ok": True, "detail": f"{_OK} ({n} propiedad{'es' if n != 1 else ''})"}
        return {"ok": False, "detail": _BAD_CREDENTIAL}
    except AuthError:
        return {
            "ok": False,
            "detail": "Beds24 rechazó el token: genera un código de invitación y usa Canjear",
        }
    except Exception:
        return {"ok": False, "detail": _UNAVAILABLE}
    finally:
        await adapter.aclose()


async def _test_webhook(session: AsyncSession) -> dict:
    """La clave de avisos no se "prueba" contra un proveedor: se informa su actividad."""
    from app.services import webhook_service

    st = await webhook_service.status(session)
    if not st["configured"]:
        return {"ok": False, "detail": "sin configurar"}
    if st["last_accepted_at"]:
        return {"ok": True, "detail": f"último aviso: {st['last_accepted_at'][:16].replace('T', ' ')} UTC"}
    return {"ok": True, "detail": "clave guardada; sin avisos aún"}


@router.post("/{name}/test")
async def test_secret(name: str, session: AsyncSession = Depends(get_session)):
    meta = SECRET_NAMES.get(name)
    if meta is None:
        raise HTTPException(status_code=404, detail="Secreto no gestionable")
    kind = meta["test"]
    if kind == "llm":
        return await _test_llm(name)
    if kind == "search":
        return await _test_search()
    if kind == "webhook":
        return await _test_webhook(session)
    return await _test_beds24()
