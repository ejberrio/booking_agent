from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MessageRole
from app.models.mixins import JSONBType, TimestampMixin


class LLMConfig(Base, TimestampMixin):
    __tablename__ = "llm_config"

    provider: Mapped[str] = mapped_column(String(60), default="openai")
    model_general: Mapped[str] = mapped_column(String(80), default="gpt-4o-mini")
    model_actions: Mapped[str] = mapped_column(String(80), default="gpt-4o")
    budget_usd_per_day: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    params: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversation"

    title: Mapped[str | None] = mapped_column(String(300), nullable=True)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base, TimestampMixin):
    __tablename__ = "message"

    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversation.id"), index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
