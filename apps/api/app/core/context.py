"""Contexto de cada petición (feature 026): cuenta y usuario, derivados SOLO de la sesión.

La cuenta nunca sale de un parámetro del navegador ni del agente (principio VI).
`require_ctx` fija la cuenta en la sesión de base de datos de la petición, y el filtro
automático de `app/db/tenancy.py` hace el resto.
"""

from __future__ import annotations

from dataclasses import dataclass

import json

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.db.tenancy import set_tenant
from app.models.account import FIRST_ACCOUNT_ID


@dataclass(frozen=True)
class RequestContext:
    account_id: int
    user_id: int | None = None
    is_platform_admin: bool = False
    session_kind: str | None = None  # "web" | "app" (sesiones de usuario)


async def current_identity(
    request: Request, session: AsyncSession = Depends(get_session)
) -> RequestContext:
    """Quién hace la petición. Las pruebas de aislamiento sustituyen SOLO esta pieza."""
    if settings.auth_mode == "legacy":
        # Transición (PR1): la web aún valida la contraseña única; todo es de la cuenta 1.
        return RequestContext(account_id=FIRST_ACCOUNT_ID, is_platform_admin=True)
    # pragma: no cover — se implementa con las sesiones de usuario (PR2)
    raise HTTPException(status_code=401, detail="Sesión no válida")


async def require_ctx(
    request: Request,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(current_identity),
) -> RequestContext:
    """Fija la cuenta de la petición en la sesión de base de datos (filtro automático)."""
    set_tenant(session, ctx.account_id, ctx.user_id)
    request.state.ctx = ctx
    await _ensure_unit_param(request, session)
    return ctx


async def _ensure_unit_param(request: Request, session: AsyncSession) -> None:
    """`unit_type_id` (query o cuerpo JSON) de otra cuenta → 404, igual que uno inexistente.

    Defensa uniforme para ~40 rutas: el filtro por cuenta ya impide leer o escribir datos
    ajenos; esto da además la respuesta honesta "no existe" antes de tocar servicios.
    """
    from app.models.property import UnitType

    raw = request.query_params.get("unit_type_id")
    if raw is None and request.method in ("POST", "PUT", "PATCH"):
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = json.loads(await request.body() or b"{}")
            except ValueError:
                body = None
            if isinstance(body, dict):
                raw = body.get("unit_type_id")
    if raw is None:
        return
    try:
        uid = int(raw)
    except (TypeError, ValueError):
        return  # la validación de la ruta responde 422
    if await session.get(UnitType, uid) is None:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")


async def require_platform_admin(ctx: RequestContext = Depends(require_ctx)) -> RequestContext:
    if not ctx.is_platform_admin:
        raise HTTPException(status_code=403, detail="Solo el administrador de la plataforma")
    return ctx
