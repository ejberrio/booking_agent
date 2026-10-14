"""Usuarios, membresías y sesiones (feature 026, entrega 2).

Las contraseñas se guardan con Argon2id (nunca recuperables); los tokens de sesión y de
enlaces de un solo uso se guardan solo como SHA-256. Ninguna de estas tablas usa el
filtro por cuenta: las consultan los servicios de acceso de forma explícita.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, _now


class AppUser(Base, TimestampMixin):
    __tablename__ = "app_user"

    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    language: Mapped[str] = mapped_column(String(5), default="es")
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Resumen semanal por correo (feature 030); se apaga desde el correo o en Ajustes.
    weekly_digest: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Membership(Base, TimestampMixin):
    """Usuario ↔ cuenta. Hoy cada usuario tiene una y cada cuenta un dueño."""

    __tablename__ = "membership"
    __table_args__ = (UniqueConstraint("user_id", "account_id", name="uq_membership_user_account"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="owner")


class UserSession(Base, TimestampMixin):
    """Sesión revocable. `kind`: web (7 días) | app (90 días)."""

    __tablename__ = "user_session"

    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(8), default="web")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)


class AuthToken(Base, TimestampMixin):
    """Enlace o estado de un solo uso: verify_email | reset_password | oauth_state | app_handoff."""

    __tablename__ = "auth_token"

    purpose: Mapped[str] = mapped_column(String(20), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthAttempt(Base, TimestampMixin):
    """Intento de acceso (para limitar fuerza bruta). Sin el correo en claro."""

    __tablename__ = "auth_attempt"

    email_hash: Mapped[str] = mapped_column(String(64), index=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)


class InviteCode(Base, TimestampMixin):
    """Código de invitación de un solo uso (beta por invitación, feature 026). Solo se guarda
    el hash y los últimos 4 caracteres: el código completo se muestra una vez al crearlo."""

    __tablename__ = "invite_code"

    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last4: Mapped[str] = mapped_column(String(4))
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_account_id: Mapped[int | None] = mapped_column(ForeignKey("account.id"), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlatformSetting(Base):
    """Ajustes de la plataforma (clave → valor). Hoy: registration_open."""

    __tablename__ = "platform_setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class TermsAcceptance(Base, TimestampMixin):
    """Aceptación de los Términos y la Política de privacidad (feature 028). Una fila por
    versión aceptada: se conserva el historial."""

    __tablename__ = "terms_acceptance"

    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), index=True)
    version: Mapped[str] = mapped_column(String(20))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
