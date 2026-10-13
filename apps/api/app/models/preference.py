"""Preferencias del host (feature 021). Una fila por cuenta (feature 026)."""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.account import AccountOwned
from app.models.mixins import TimestampMixin

LANGUAGES = ("es", "en", "pt")


class AppPreference(Base, AccountOwned, TimestampMixin):
    __tablename__ = "app_preference"
    __table_args__ = (UniqueConstraint("account_id", name="uq_app_preference_account"),)

    language: Mapped[str] = mapped_column(String(5), default="es")
