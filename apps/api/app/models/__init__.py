"""Modelos ORM del dominio. Importar todo aquí para que Alembic detecte la metadata."""

from app.models.agent import AgentAction, Conversation, LLMConfig, Message
from app.models.intelligence import IntelligenceRun, MarketReference
from app.models.audit import PriceChangeLog, PromotionChangeLog
from app.models.availability import AvailabilityChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay, CalendarNote, Rate
from app.models.market import Event, PriceSuggestion
from app.models.pricing import NativeDeal, PricingRule, Promotion
from app.models.property import Channel, Property, UnitType
from app.models.sync import ChannelManagerConnection, SyncIssue, SyncRun

__all__ = [
    "Property",
    "Channel",
    "UnitType",
    "CalendarDay",
    "CalendarNote",
    "Rate",
    "PricingRule",
    "Promotion",
    "NativeDeal",
    "Booking",
    "Event",
    "PriceSuggestion",
    "PriceChangeLog",
    "AvailabilityChangeLog",
    "LLMConfig",
    "Conversation",
    "Message",
    "ChannelManagerConnection",
    "SyncRun",
    "SyncIssue",
    "PromotionChangeLog",
    "AgentAction",
    "MarketReference",
    "IntelligenceRun",
]
