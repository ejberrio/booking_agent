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

    adapter = get_adapter()
    try:
        info = await adapter.test_connection()
        if info.ok:
            n = len(info.properties or [])
            return {"ok": True, "detail": f"{_OK} ({n} propiedad{'es' if n != 1 else ''})"}
        return {"ok": False, "detail": _BAD_CREDENTIAL}
    except Exception:
        return {"ok": False, "detail": _UNAVAILABLE}
    finally:
        await adapter.aclose()


@router.post("/{name}/test")
async def test_secret(name: str):
    meta = SECRET_NAMES.get(name)
    if meta is None:
        raise HTTPException(status_code=404, detail="Secreto no gestionable")
    kind = meta["test"]
    if kind == "llm":
        return await _test_llm(name)
    if kind == "search":
        return await _test_search()
    return await _test_beds24()
