"""Límite de intentos de acceso (feature 026, SC-007): 10 fallos seguidos por correo o 50 por
IP en 15 minutos bloquean temporalmente. Persistente (sobrevive reinicios)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import email_digest
from app.models.auth import AuthAttempt
from app.models.mixins import _now

WINDOW = timedelta(minutes=15)
MAX_PER_EMAIL = 10
MAX_PER_IP = 50
RETENTION = timedelta(days=7)


async def is_blocked(session: AsyncSession, email: str, ip: str | None) -> bool:
    since = _now() - WINDOW
    h = email_digest(email)
    last_ok = (
        await session.execute(
            select(func.max(AuthAttempt.created_at)).where(
                AuthAttempt.email_hash == h, AuthAttempt.success.is_(True)
            )
        )
    ).scalar()
    start = max(since, last_ok) if last_ok and last_ok.tzinfo else since
    fails = (
        await session.execute(
            select(func.count()).where(
                AuthAttempt.email_hash == h,
                AuthAttempt.success.is_(False),
                AuthAttempt.created_at > start,
            )
        )
    ).scalar_one()
    if fails >= MAX_PER_EMAIL:
        return True
    if ip:
        by_ip = (
            await session.execute(
                select(func.count()).where(
                    AuthAttempt.ip == ip,
                    AuthAttempt.success.is_(False),
                    AuthAttempt.created_at > since,
                )
            )
        ).scalar_one()
        if by_ip >= MAX_PER_IP:
            return True
    return False


async def record(session: AsyncSession, email: str, ip: str | None, success: bool) -> None:
    await session.execute(delete(AuthAttempt).where(AuthAttempt.created_at < _now() - RETENTION))
    session.add(AuthAttempt(email_hash=email_digest(email), ip=(ip or None) and ip[:64],
                            success=success))
    await session.flush()
