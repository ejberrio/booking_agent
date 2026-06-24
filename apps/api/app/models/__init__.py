"""Modelos ORM del dominio. Importar todo aquí para que Alembic detecte la metadata."""

from app.models.agent import Conversation, LLMConfig, Message
from app.models.audit import PriceChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay, Rate
from app.models.market import Event, PriceSuggestion
from app.models.pricing import PricingRule, Promotion
from app.models.property import Channel, Property, UnitType
from app.models.sync import ChannelManagerConnection, SyncIssue, SyncRun

__all__ = [
    "Property",
    "Channel",
    "UnitType",
    "CalendarDay",
    "Rate",
    "PricingRule",
    "Promotion",
    "Booking",
    "Event",
    "PriceSuggestion",
    "PriceChangeLog",
    "LLMConfig",
    "Conversation",
    "Message",
    "ChannelManagerConnection",
    "SyncRun",
    "SyncIssue",
]
