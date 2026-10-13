"""Cuentas (feature 026): cada anfitrión es una cuenta dueña de sus datos.

`AccountOwned` marca las tablas con datos de un anfitrión. El filtro automático de
`app/db/tenancy.py` limita toda lectura/escritura del ORM a la cuenta del contexto
(principio VI de la constitución: aislamiento por cuenta, no negociable).
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin

#: Cuenta del host original: recibe todos los datos existentes en la migración.
FIRST_ACCOUNT_ID = 1


class AccountStatus(enum.StrEnum):
    active = "active"
    disabled = "disabled"


class Account(Base, TimestampMixin):
    __tablename__ = "account"

    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="accountstatus"), default=AccountStatus.active
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountOwned:
    """Mixin: la fila pertenece a exactamente una cuenta (FK NOT NULL indexada)."""

    @declared_attr
    def account_id(cls) -> Mapped[int]:  # noqa: N805 — declared_attr recibe la clase
        return mapped_column(ForeignKey("account.id"), index=True)
