"""Acceso por usuario (feature 026, entrega 2).

Sesiones opacas y revocables (hash en base de datos), contraseñas Argon2id, enlaces de un
solo uso para verificar el correo y recuperar la contraseña, límite de intentos, y la
reclamación de la cuenta nº 1 por el host original. Mensajes de error genéricos: nunca
revelan si un correo existe. Nada de este módulo registra correos, tokens ni contraseñas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import passwords, ratelimit
from app.auth.tokens import digest, new_token, normalize_email
from app.core.config import settings
from app.email import templates
from app.email.base import EmailSender
from app.models.account import FIRST_ACCOUNT_ID, Account, AccountStatus
from app.models.auth import AppUser, AuthToken, Membership, UserSession
from app.models.mixins import _now

SESSION_TTL = {"web": timedelta(days=7), "app": timedelta(days=90)}
VERIFY_TTL = timedelta(hours=24)
RESET_TTL = timedelta(hours=1)
TOUCH_EVERY = timedelta(minutes=5)
LANGS = ("es", "en", "pt")


class AuthError(Exception):
    """Error de acceso con código estable para la web y estado HTTP."""

    def __init__(self, code: str, detail: str, status: int = 400):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class Resolved:
    user: AppUser
    account_id: int
    kind: str


def get_email_sender() -> EmailSender | None:
    """Adaptador de correo vigente o None si no hay clave (secreto de plataforma)."""
    from app.email.resend import ResendSender
    from app.services.secret_service import get_secret

    key = get_secret("email_api_key")
    return ResendSender(key) if key else None


def _aware(dt: datetime | None) -> datetime | None:
    # SQLite (pruebas) devuelve fechas sin zona; PostgreSQL con zona.
    if dt is not None and dt.tzinfo is None:
        from datetime import UTC

        return dt.replace(tzinfo=UTC)
    return dt


def _link(path: str, token: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}{path}?token={token}"


# --------- sesiones ---------


async def create_session(
    session: AsyncSession, user: AppUser, kind: str = "web", user_agent: str | None = None
) -> tuple[str, datetime]:
    kind = kind if kind in SESSION_TTL else "web"
    token = new_token()
    expires = _now() + SESSION_TTL[kind]
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=digest(token),
            kind=kind,
            expires_at=expires,
            last_used_at=_now(),
            user_agent=(user_agent or "")[:200] or None,
        )
    )
    user.last_login_at = _now()
    member = await _membership(session, user.id)
    account = await session.get(Account, member.account_id) if member else None
    if account is not None:
        account.last_seen_at = _now()
    await session.flush()
    return token, expires


async def _membership(session: AsyncSession, user_id: int) -> Membership | None:
    return (
        await session.execute(
            select(Membership).where(Membership.user_id == user_id).order_by(Membership.id)
        )
    ).scalars().first()


async def resolve_session(session: AsyncSession, token: str) -> Resolved | None:
    """Sesión válida → usuario y cuenta activos. Cualquier otra cosa → None."""
    if not token:
        return None
    row = (
        await session.execute(select(UserSession).where(UserSession.token_hash == digest(token)))
    ).scalar_one_or_none()
    now = _now()
    if row is None or row.revoked_at is not None or _aware(row.expires_at) <= now:
        return None
    user = await session.get(AppUser, row.user_id)
    member = await _membership(session, row.user_id) if user else None
    account = await session.get(Account, member.account_id) if member else None
    if user is None or account is None or account.status != AccountStatus.active:
        return None
    if now - _aware(row.last_used_at) > TOUCH_EVERY:
        row.last_used_at = now
        account.last_seen_at = now
        await session.commit()
    return Resolved(user=user, account_id=account.id, kind=row.kind)


async def revoke(session: AsyncSession, token: str) -> None:
    await session.execute(
        update(UserSession)
        .where(UserSession.token_hash == digest(token), UserSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    await session.flush()


async def revoke_all(session: AsyncSession, user_id: int, *, keep_token: str | None = None) -> None:
    stmt = update(UserSession).where(
        UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
    )
    if keep_token:
        stmt = stmt.where(UserSession.token_hash != digest(keep_token))
    await session.execute(stmt.values(revoked_at=_now()))
    await session.flush()


# --------- acceso ---------


async def _user_by_email(session: AsyncSession, email: str) -> AppUser | None:
    return (
        await session.execute(select(AppUser).where(AppUser.email == normalize_email(email)))
    ).scalar_one_or_none()


async def login(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    kind: str = "web",
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, datetime, AppUser]:
    if await ratelimit.is_blocked(session, email, ip):
        raise AuthError(
            "too_many", "Demasiados intentos. Espera 15 minutos e inténtalo de nuevo.", 429
        )
    user = await _user_by_email(session, email)
    ok = bool(user) and passwords.verify_password(user.password_hash, password)
    await ratelimit.record(session, email, ip, ok)
    if not ok:
        await session.commit()
        raise AuthError("invalid", "Correo o contraseña incorrectos", 401)
    member = await _membership(session, user.id)
    account = await session.get(Account, member.account_id) if member else None
    if account is None or account.status != AccountStatus.active:
        await session.commit()
        raise AuthError("disabled", "Esta cuenta está desactivada", 403)
    # El dueño original (administrador) puede entrar sin verificar: reclamó con la clave actual.
    if user.email_verified_at is None and not user.is_platform_admin:
        await session.commit()
        raise AuthError("email_unverified", "Verifica tu correo para entrar", 403)
    if passwords.needs_rehash(user.password_hash):
        user.password_hash = passwords.hash_password(password)
    token, expires = await create_session(session, user, kind, user_agent)
    await session.commit()
    return token, expires, user


# --------- enlaces de un solo uso ---------


async def _issue(session: AsyncSession, purpose: str, user: AppUser, ttl: timedelta) -> str:
    # Un enlace nuevo invalida los anteriores del mismo propósito.
    await session.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
        .values(used_at=_now())
    )
    token = new_token()
    session.add(
        AuthToken(purpose=purpose, token_hash=digest(token), user_id=user.id,
                  expires_at=_now() + ttl)
    )
    await session.flush()
    return token


async def _consume(session: AsyncSession, purpose: str, token: str) -> AppUser:
    row = (
        await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == digest(token or ""), AuthToken.purpose == purpose
            )
        )
    ).scalar_one_or_none()
    if row is None or row.used_at is not None or _aware(row.expires_at) <= _now():
        raise AuthError("link_invalid", "El enlace venció o ya se usó. Pide uno nuevo.", 400)
    row.used_at = _now()
    user = await session.get(AppUser, row.user_id)
    if user is None:
        raise AuthError("link_invalid", "El enlace venció o ya se usó. Pide uno nuevo.", 400)
    return user


async def send_verification(
    session: AsyncSession, user: AppUser, sender: EmailSender | None = None
) -> bool:
    sender = sender or get_email_sender()
    if sender is None or user.email_verified_at is not None:
        return False
    token = await _issue(session, "verify_email", user, VERIFY_TTL)
    await session.commit()
    return await sender.send(
        templates.verify_email(user.email, user.language, _link("/verify", token), user.name)
    )


async def resend_verification(
    session: AsyncSession, email: str, sender: EmailSender | None = None
) -> None:
    user = await _user_by_email(session, email)
    if user is not None:
        await send_verification(session, user, sender)


async def verify_email(
    session: AsyncSession, token: str, *, kind: str = "web", user_agent: str | None = None
) -> tuple[str, datetime, AppUser]:
    # Abrir el enlace dos veces (o que el correo lo "previsualice") no debe asustar: si el
    # correo ya está confirmado, se dice así en vez de "enlace vencido".
    row = (
        await session.execute(
            select(AuthToken).where(
                AuthToken.token_hash == digest(token or ""), AuthToken.purpose == "verify_email"
            )
        )
    ).scalar_one_or_none()
    if row is not None and row.used_at is not None:
        owner = await session.get(AppUser, row.user_id)
        if owner is not None and owner.email_verified_at is not None:
            raise AuthError("already_verified", "Tu correo ya está confirmado", 409)
    user = await _consume(session, "verify_email", token)
    user.email_verified_at = user.email_verified_at or _now()
    tok, expires = await create_session(session, user, kind, user_agent)
    await session.commit()
    return tok, expires, user


async def forgot_password(
    session: AsyncSession, email: str, language: str | None = None,
    sender: EmailSender | None = None,
) -> None:
    """Siempre "revisa tu correo": nunca revela si el correo existe."""
    sender = sender or get_email_sender()
    user = await _user_by_email(session, email)
    if user is None or sender is None:
        return
    token = await _issue(session, "reset_password", user, RESET_TTL)
    await session.commit()
    lang = language if language in LANGS else user.language
    await sender.send(
        templates.reset_password(user.email, lang, _link("/reset", token), user.name)
    )


async def reset_password(session: AsyncSession, token: str, password: str) -> None:
    passwords.check_policy(password)
    user = await _consume(session, "reset_password", token)
    user.password_hash = passwords.hash_password(password)
    # Quien recibe el enlace en su correo prueba que el correo es suyo.
    user.email_verified_at = user.email_verified_at or _now()
    await revoke_all(session, user.id)
    await session.commit()


async def change_password(
    session: AsyncSession, user: AppUser, current: str, new: str, keep_token: str
) -> None:
    if user.password_hash and not passwords.verify_password(user.password_hash, current):
        raise AuthError("invalid", "La contraseña actual no es correcta", 400)
    passwords.check_policy(new)
    user.password_hash = passwords.hash_password(new)
    await revoke_all(session, user.id, keep_token=keep_token)
    await session.commit()


# --------- registro (entrega 3) ---------


async def register(
    session: AsyncSession,
    *,
    name: str,
    email: str,
    password: str,
    invite_code: str | None = None,
    language: str = "es",
    sender: EmailSender | None = None,
) -> None:
    """Crea cuenta + usuario dueño. Con el registro cerrado exige un código vigente.

    La respuesta es la misma exista o no el correo: si ya existe se le avisa por correo y el
    código NO se consume. El usuario entra tras verificar su correo.
    """
    from app.services import invite_service

    sender = sender or get_email_sender()
    if sender is None:
        raise AuthError("email_unavailable", "El registro no está disponible por ahora", 503)
    email = normalize_email(email)
    name = (name or "").strip()
    if "@" not in email or len(email) > 254 or not name:
        raise AuthError("invalid_data", "Revisa el nombre y el correo", 400)
    passwords.check_policy(password)
    open_reg = await invite_service.registration_open(session)
    invite = None
    if not open_reg:
        invite = await invite_service.find_valid(session, invite_code or "")
        if invite is None:
            code = "invite_required" if not (invite_code or "").strip() else "invite_invalid"
            raise AuthError(
                code,
                "StayLever está en beta por invitación"
                if code == "invite_required"
                else "El código de invitación no es válido, venció o ya se usó",
                400,
            )
    existing = await _user_by_email(session, email)
    lang = language if language in LANGS else "es"
    if existing is not None:
        await sender.send(
            templates.already_registered(email, lang, f"{settings.public_base_url.rstrip('/')}/login")
        )
        return
    account = Account(name=name[:120])
    session.add(account)
    await session.flush()
    if invite is not None and not await invite_service.consume(session, invite, account.id):
        await session.rollback()
        raise AuthError("invite_invalid", "El código de invitación no es válido, venció o ya se usó", 400)
    user = AppUser(
        email=email,
        name=name[:120],
        password_hash=passwords.hash_password(password),
        language=lang,
    )
    session.add(user)
    await session.flush()
    session.add(Membership(user_id=user.id, account_id=account.id, role="owner"))
    await session.commit()
    await send_verification(session, user, sender)


# --------- reclamar la cuenta nº 1 ---------


async def claim_status(session: AsyncSession) -> bool:
    """¿La cuenta nº 1 (datos del host original) sigue sin usuario?"""
    if await session.get(Account, FIRST_ACCOUNT_ID) is None:
        return False
    n = (
        await session.execute(
            select(func.count()).where(Membership.account_id == FIRST_ACCOUNT_ID)
        )
    ).scalar_one()
    return n == 0


async def claim(
    session: AsyncSession,
    *,
    name: str,
    email: str,
    password: str,
    language: str = "es",
    kind: str = "web",
    user_agent: str | None = None,
    sender: EmailSender | None = None,
) -> tuple[str, datetime, AppUser]:
    """Crea el usuario dueño de la cuenta nº 1 (y administrador de plataforma). Una sola vez:
    la web solo llama aquí tras comprobar la contraseña compartida actual."""
    if not await claim_status(session):
        raise AuthError("already_claimed", "Esta cuenta ya tiene dueño", 409)
    email = normalize_email(email)
    if "@" not in email or len(email) > 254 or not (name or "").strip():
        raise AuthError("invalid_data", "Revisa el nombre y el correo", 400)
    passwords.check_policy(password)
    if await _user_by_email(session, email) is not None:
        raise AuthError("email_taken", "Ese correo ya está registrado", 409)
    user = AppUser(
        email=email,
        name=name.strip()[:120],
        password_hash=passwords.hash_password(password),
        language=language if language in LANGS else "es",
        is_platform_admin=True,
    )
    session.add(user)
    await session.flush()
    session.add(Membership(user_id=user.id, account_id=FIRST_ACCOUNT_ID, role="owner"))
    token, expires = await create_session(session, user, kind, user_agent)
    await session.commit()
    await send_verification(session, user, sender)  # si el correo está configurado
    return token, expires, user


def me(user: AppUser, account: Account) -> dict:
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "email_verified": user.email_verified_at is not None,
            "language": user.language,
            "is_platform_admin": user.is_platform_admin,
            "has_password": bool(user.password_hash),
        },
        "account": {"id": account.id, "name": account.name},
    }
