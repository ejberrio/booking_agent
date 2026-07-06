"""Secretos gestionados desde la app (feature 017).

`value_encrypted` va cifrado con Fernet (clave derivada de SECRET_KEY) y NUNCA
sale de la API — ni en claro ni cifrado. La auditoría guarda solo la pista.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, _now


class SecretEntry(Base, TimestampMixin):
    __tablename__ = "secret_entry"

    name: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    value_encrypted: Mapped[str] = mapped_column(Text)
    hint: Mapped[str] = mapped_column(String(8), default="")


class SecretChangeLog(Base, TimestampMixin):
    """Auditoría append-only de cambios de secretos. SIN valores, jamás."""

    __tablename__ = "secret_change_log"

    name: Mapped[str] = mapped_column(String(60), index=True)
    action: Mapped[str] = mapped_column(String(12))  # "set" | "deleted"
    hint: Mapped[str] = mapped_column(String(8), default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
