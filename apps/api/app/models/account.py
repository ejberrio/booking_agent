"""Cuentas (feature 026): cada anfitrión es una cuenta dueña de sus datos.

`AccountOwned` marca las tablas con datos de un anfitrión. El filtro automático de
`app/db/tenancy.py` limita toda lectura/escritura del ORM a la cuenta del contexto
(principio VI de la constitución: aislamiento por cuenta, no negociable).
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin

#: Cuenta del host original: recibe todos los datos existentes en la migración.
FIRST_ACCOUNT_ID = 1


class AccountStatus(enum.StrEnum):
    active = "active"
    disabled = "disabled"
    #: Lápida tras la supresión (feature 028): sin nombre, usuarios ni datos.
    deleted = "deleted"


class Account(Base, TimestampMixin):
    __tablename__ = "account"

    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="accountstatus"), default=AccountStatus.active
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Límites de IA (feature 027); NULL = valor por defecto de la plataforma.
    chat_limit_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_limit_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Origen del registro (feature 030): open (registro abierto, cuenta contra el cupo),
    # invite, admin; NULL = cuentas anteriores.
    signup_source: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Feature 029: "connected" (Channel Manager) | "manual" (sin conexión: StayLever guarda los
    # precios y el anfitrión los aplica a mano en cada plataforma; nada se publica).
    channel_mode: Mapped[str] = mapped_column(String(12), default="connected")


class AccountOwned:
    """Mixin: la fila pertenece a exactamente una cuenta (FK NOT NULL indexada)."""

    @declared_attr
    def account_id(cls) -> Mapped[int]:  # noqa: N805 — declared_attr recibe la clase
        return mapped_column(ForeignKey("account.id"), index=True)


class UserStamped:
    """Mixin: guarda qué usuario hizo el cambio (auditoría, feature 026). Lo rellena
    `before_flush` con el usuario de la sesión; NULL = sistema/cron."""

    @declared_attr
    def user_id(cls) -> Mapped[int | None]:  # noqa: N805
        return mapped_column(ForeignKey("app_user.id"), nullable=True)
