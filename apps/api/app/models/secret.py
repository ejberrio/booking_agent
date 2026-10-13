"""Secretos gestionados desde la app (feature 017).

`value_encrypted` va cifrado con Fernet (clave derivada de SECRET_KEY) y NUNCA
sale de la API — ni en claro ni cifrado. La auditoría guarda solo la pista.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, _now


class SecretEntry(Base, TimestampMixin):
    """Secreto de la plataforma (account_id NULL) o de una cuenta (feature 026).

    No usa el filtro automático por cuenta: `secret_service` filtra explícitamente.
    """

    __tablename__ = "secret_entry"
    __table_args__ = (
        Index(
            "uq_secret_platform_name",
            "name",
            unique=True,
            postgresql_where=text("account_id IS NULL"),
            sqlite_where=text("account_id IS NULL"),
        ),
        Index(
            "uq_secret_account_name",
            "account_id",
            "name",
            unique=True,
            postgresql_where=text("account_id IS NOT NULL"),
            sqlite_where=text("account_id IS NOT NULL"),
        ),
    )

    account_id: Mapped[int | None] = mapped_column(ForeignKey("account.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(60), index=True)
    value_encrypted: Mapped[str] = mapped_column(Text)
    hint: Mapped[str] = mapped_column(String(8), default="")


class SecretChangeLog(Base, TimestampMixin):
    """Auditoría append-only de cambios de secretos. SIN valores, jamás."""

    __tablename__ = "secret_change_log"

    account_id: Mapped[int | None] = mapped_column(ForeignKey("account.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(60), index=True)
    action: Mapped[str] = mapped_column(String(12))  # "set" | "deleted"
    hint: Mapped[str] = mapped_column(String(8), default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
