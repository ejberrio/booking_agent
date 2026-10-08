"""Preferencias del host (feature 021). Single-tenant: una sola fila (id=1)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin

LANGUAGES = ("es", "en", "pt")


class AppPreference(Base, TimestampMixin):
    __tablename__ = "app_preference"

    language: Mapped[str] = mapped_column(String(5), default="es")
