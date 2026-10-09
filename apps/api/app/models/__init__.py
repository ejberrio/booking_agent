"""Modelos ORM del dominio. Importar todo aquí para que Alembic detecte la metadata."""

from app.models.agent import AgentAction, Conversation, LLMConfig, Message
from app.models.intelligence import IntelligenceRun, MarketReference, ScanConfig
from app.models.audit import PriceChangeLog, PromotionChangeLog
from app.models.availability import AvailabilityChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay, CalendarNote, Rate
from app.models.market import Event, PointOfInterest, PriceSuggestion
from app.models.pricing import NativeDeal, PricingRule, Promotion
from app.models.preference import AppPreference
from app.models.property import Channel, Property, UnitType
from app.models.push import PushDevice, PushNotificationLog
from app.models.secret import SecretChangeLog, SecretEntry
from app.models.sync import ChannelManagerConnection, SyncIssue, SyncRun
from app.models.webhook import WebhookEvent

__all__ = [
    "AppPreference",
    "PushDevice",
    "PushNotificationLog",
    "WebhookEvent",
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
    "ScanConfig",
    "PointOfInterest",
    "SecretEntry",
    "SecretChangeLog",
]
