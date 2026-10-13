"""Rutas de acceso (feature 026, entrega 2). Las llama SOLO la web desde su servidor (el proxy
del navegador las bloquea): así la cookie httpOnly y la IP del límite de intentos son fiables.
Ninguna respuesta incluye contraseñas ni hashes; los tokens solo van a la web para su cookie.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import WeakPassword
from app.core.context import RequestContext, bearer_token, require_ctx
from app.db.session import get_session
from app.models.account import Account
from app.models.auth import AppUser
from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter()

Kind = Literal["web", "app"]


def _error(exc: AuthError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": exc.detail, "code": exc.code})


def _weak(exc: WeakPassword) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc), "code": "weak_password"})


def _session_out(token: str, expires, user: AppUser) -> dict:
    return {"token": token, "expires_at": expires.isoformat(), "user": {"name": user.name}}


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)
    kind: Kind = "web"
    ip: str | None = None


@router.post("/login")
async def login(req: LoginRequest, request: Request, session: AsyncSession = Depends(get_session)):
    try:
        token, expires, user = await auth_service.login(
            session, email=req.email, password=req.password, kind=req.kind, ip=req.ip,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as exc:
        return _error(exc)
    return _session_out(token, expires, user)


class TokenRequest(BaseModel):
    token: str = Field(max_length=200)
    kind: Kind = "web"


@router.post("/verify-email")
async def verify_email(
    req: TokenRequest, request: Request, session: AsyncSession = Depends(get_session)
):
    try:
        token, expires, user = await auth_service.verify_email(
            session, req.token, kind=req.kind, user_agent=request.headers.get("user-agent")
        )
    except AuthError as exc:
        return _error(exc)
    return _session_out(token, expires, user)


class EmailRequest(BaseModel):
    email: str = Field(max_length=254)
    language: str | None = None


@router.post("/resend-verification", status_code=202)
async def resend_verification(req: EmailRequest, session: AsyncSession = Depends(get_session)):
    await auth_service.resend_verification(session, req.email)
    return {"status": "check_email"}


@router.post("/forgot-password", status_code=202)
async def forgot_password(req: EmailRequest, session: AsyncSession = Depends(get_session)):
    await auth_service.forgot_password(session, req.email, req.language)
    return {"status": "check_email"}


class ResetRequest(BaseModel):
    token: str = Field(max_length=200)
    password: str = Field(max_length=256)


@router.post("/reset-password")
async def reset_password(req: ResetRequest, session: AsyncSession = Depends(get_session)):
    try:
        await auth_service.reset_password(session, req.token, req.password)
    except WeakPassword as exc:
        return _weak(exc)
    except AuthError as exc:
        return _error(exc)
    return {"status": "ok"}


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)
    invite_code: str | None = Field(default=None, max_length=40)
    language: str = "es"


@router.post("/register", status_code=202)
async def register(req: RegisterRequest, session: AsyncSession = Depends(get_session)):
    try:
        await auth_service.register(
            session, name=req.name, email=req.email, password=req.password,
            invite_code=req.invite_code, language=req.language,
        )
    except WeakPassword as exc:
        return _weak(exc)
    except AuthError as exc:
        return _error(exc)
    return {"status": "check_email"}


@router.get("/registration-status")
async def registration_status(session: AsyncSession = Depends(get_session)):
    from app.services import invite_service

    return {"open": await invite_service.registration_open(session)}


@router.get("/claim-status")
async def claim_status(session: AsyncSession = Depends(get_session)):
    return {"claimable": await auth_service.claim_status(session)}


class ClaimRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)
    language: str = "es"
    kind: Kind = "web"


@router.post("/claim")
async def claim(req: ClaimRequest, request: Request, session: AsyncSession = Depends(get_session)):
    try:
        token, expires, user = await auth_service.claim(
            session, name=req.name, email=req.email, password=req.password,
            language=req.language, kind=req.kind, user_agent=request.headers.get("user-agent"),
        )
    except WeakPassword as exc:
        return _weak(exc)
    except AuthError as exc:
        return _error(exc)
    return _session_out(token, expires, user)


# --------- con sesión ---------


async def _current(session: AsyncSession, ctx: RequestContext) -> tuple[AppUser, Account]:
    if ctx.user_id is None:
        raise HTTPException(status_code=401, detail="Sesión no válida")
    user = await session.get(AppUser, ctx.user_id)
    account = await session.get(Account, ctx.account_id)
    if user is None or account is None:  # pragma: no cover
        raise HTTPException(status_code=401, detail="Sesión no válida")
    return user, account


@router.get("/me")
async def me(session: AsyncSession = Depends(get_session), ctx: RequestContext = Depends(require_ctx)):
    user, account = await _current(session, ctx)
    return auth_service.me(user, account)


@router.post("/logout", status_code=204)
async def logout(request: Request, session: AsyncSession = Depends(get_session)):
    token = bearer_token(request)
    if token:
        await auth_service.revoke(session, token)
        await session.commit()


@router.post("/logout-all", status_code=204)
async def logout_all(
    session: AsyncSession = Depends(get_session), ctx: RequestContext = Depends(require_ctx)
):
    user, _ = await _current(session, ctx)
    await auth_service.revoke_all(session, user.id)
    await session.commit()


class ChangePasswordRequest(BaseModel):
    current: str = Field(default="", max_length=256)
    new: str = Field(max_length=256)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_ctx),
):
    user, _ = await _current(session, ctx)
    try:
        await auth_service.change_password(
            session, user, req.current, req.new, keep_token=bearer_token(request) or ""
        )
    except WeakPassword as exc:
        return _weak(exc)
    except AuthError as exc:
        return _error(exc)
    return {"status": "ok"}


@router.post("/send-verification", status_code=202)
async def send_verification(
    session: AsyncSession = Depends(get_session), ctx: RequestContext = Depends(require_ctx)
):
    user, _ = await _current(session, ctx)
    sent = await auth_service.send_verification(session, user)
    return {"sent": sent}
