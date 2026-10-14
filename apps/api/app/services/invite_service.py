"""Códigos de invitación (feature 026, entrega 3): beta por invitación.

Formato `SL-XXXX-XXXX` (Crockford base32: sin I, L, O, U para evitar confusiones). Se guarda
solo el hash; el código completo se muestra UNA vez al crearlo. El consumo es atómico: dos
registros simultáneos con el mismo código → solo uno lo usa.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import digest
from app.models.account import Account
from app.models.auth import InviteCode, PlatformSetting
from app.models.mixins import _now

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
DEFAULT_DAYS = 30
REGISTRATION_OPEN = "registration_open"


def _aware(dt):
    if dt is not None and dt.tzinfo is None:
        from datetime import UTC

        return dt.replace(tzinfo=UTC)
    return dt


def normalize_code(code: str) -> str:
    """'sl-ab12 cd34' → 'SL-AB12-CD34' (tolera minúsculas, espacios y O/I/L)."""
    raw = "".join(ch for ch in (code or "").upper() if ch.isalnum())
    raw = raw.replace("O", "0").replace("I", "1").replace("L", "1")
    if raw.startswith("S1"):  # "SL" con L→1
        raw = "SL" + raw[2:]
    if not raw.startswith("SL") or len(raw) != 10:
        return ""
    return f"SL-{raw[2:6]}-{raw[6:10]}"


def _new_code() -> str:
    body = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return f"SL-{body[:4]}-{body[4:]}"


def status_of(inv: InviteCode) -> str:
    if inv.used_at is not None:
        return "used"
    if inv.revoked_at is not None:
        return "revoked"
    if _aware(inv.expires_at) <= _now():
        return "expired"
    return "active"


async def create(
    session: AsyncSession, *, note: str | None, days: int = DEFAULT_DAYS, by_user_id: int | None
) -> tuple[InviteCode, str]:
    days = max(1, min(int(days or DEFAULT_DAYS), 180))
    code = _new_code()
    inv = InviteCode(
        code_hash=digest(code),
        last4=code[-4:],
        note=(note or "").strip()[:200] or None,
        expires_at=_now() + timedelta(days=days),
        created_by_user_id=by_user_id,
    )
    session.add(inv)
    await session.flush()
    return inv, code


async def list_invites(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(InviteCode, Account.name)
            .outerjoin(Account, InviteCode.used_by_account_id == Account.id)
            .order_by(InviteCode.id.desc())
        )
    ).all()
    return [
        {
            "id": inv.id,
            "last4": inv.last4,
            "note": inv.note,
            "status": status_of(inv),
            "expires_at": _aware(inv.expires_at).isoformat(),
            "created_at": _aware(inv.created_at).isoformat() if inv.created_at else None,
            "used_by_account": (
                {"id": inv.used_by_account_id, "name": acc_name}
                if inv.used_by_account_id is not None
                else None
            ),
        }
        for inv, acc_name in rows
    ]


async def revoke(session: AsyncSession, invite_id: int) -> None:
    inv = await session.get(InviteCode, invite_id)
    if inv is None:
        raise LookupError("No existe esa invitación")
    if inv.used_at is not None:
        raise ValueError("Esa invitación ya se usó")
    inv.revoked_at = inv.revoked_at or _now()
    await session.flush()


async def find_valid(session: AsyncSession, code: str) -> InviteCode | None:
    norm = normalize_code(code)
    if not norm:
        return None
    inv = (
        await session.execute(select(InviteCode).where(InviteCode.code_hash == digest(norm)))
    ).scalar_one_or_none()
    return inv if inv is not None and status_of(inv) == "active" else None


async def consume(session: AsyncSession, inv: InviteCode, account_id: int) -> bool:
    """Marca el código como usado SOLO si nadie lo usó antes (UPDATE condicional)."""
    res = await session.execute(
        update(InviteCode)
        .where(
            InviteCode.id == inv.id,
            InviteCode.used_at.is_(None),
            InviteCode.revoked_at.is_(None),
        )
        .values(used_at=_now(), used_by_account_id=account_id)
    )
    return res.rowcount == 1


DEFAULT_QUOTA = 50
DEFAULT_CITY_BUDGET = 20


async def _setting(session: AsyncSession) -> dict:
    row = await session.get(PlatformSetting, REGISTRATION_OPEN)
    return dict(row.value) if row is not None and isinstance(row.value, dict) else {}


async def open_accounts(session: AsyncSession) -> int:
    """Cuentas del registro abierto que cuentan contra el cupo (las borradas lo liberan)."""
    from sqlalchemy import func

    from app.models.account import AccountStatus

    return (
        await session.execute(
            select(func.count()).select_from(Account).where(
                Account.signup_source == "open", Account.status != AccountStatus.deleted
            )
        )
    ).scalar_one()


async def registration_state(session: AsyncSession) -> dict:
    """Registro abierto con cupo (feature 030): {enabled, quota, used, full, open, city_budget}."""
    v = await _setting(session)
    enabled = bool(v.get("enabled"))
    quota = int(v.get("quota") or DEFAULT_QUOTA)
    used = await open_accounts(session)
    full = used >= quota
    return {
        "enabled": enabled,
        "quota": quota,
        "used": used,
        "full": enabled and full,
        "open": enabled and not full,
        "city_budget": int(v.get("city_budget") or DEFAULT_CITY_BUDGET),
    }


async def registration_open(session: AsyncSession) -> bool:
    """Se puede registrar sin invitación: encendido y con cupo."""
    return (await registration_state(session))["open"]


async def update_registration(
    session: AsyncSession, *, enabled: bool | None = None, quota: int | None = None,
    city_budget: int | None = None,
) -> None:
    v = await _setting(session)
    if enabled is not None:
        v["enabled"] = bool(enabled)
    if quota is not None:
        v["quota"] = max(0, min(int(quota), 100000))
    if city_budget is not None:
        v["city_budget"] = max(0, min(int(city_budget), 1000))
    row = await session.get(PlatformSetting, REGISTRATION_OPEN)
    if row is None:
        session.add(PlatformSetting(key=REGISTRATION_OPEN, value=v))
    else:
        row.value = v  # nuevo dict: SQLAlchemy detecta el cambio del JSON
    await session.flush()


async def set_registration_open(session: AsyncSession, enabled: bool) -> None:
    await update_registration(session, enabled=enabled)
