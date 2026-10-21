"""Modelos ORM del dominio. Importar todo aquí para que Alembic detecte la metadata."""

from app.models.account import Account
from app.models.auth import (
    AppUser,
    AuthAttempt,
    AuthToken,
    InviteCode,
    Membership,
    PlatformSetting,
    TermsAcceptance,
    UserSession,
)
from app.models.agent import AgentAction, Conversation, LLMConfig, Message
from app.models.intelligence import IntelligenceRun, MarketReference, ScanConfig
from app.models.audit import PriceChangeLog, PromotionChangeLog
from app.models.availability import AvailabilityChangeLog
from app.models.booking import Booking
from app.models.calendar import CalendarDay, CalendarNote, Rate
from app.models.market import (
    Event,
    EventReport,
    MarketBand,
    MarketFeed,
    PointOfInterest,
    PriceSuggestion,
)
from app.models.pricing import NativeDeal, PricingRule, Promotion
from app.models.usage import AIUsage
from app.models.public import CityScan, PublicMetric, PublicQuota, PublicReport, WaitlistEntry
from app.models.preference import AppPreference
from app.models.property import Channel, Property, UnitType
from app.models.push import PushDevice, PushNotificationLog
from app.models.secret import SecretChangeLog, SecretEntry
from app.models.sync import ChannelManagerConnection, SyncIssue, SyncRun
from app.models.webhook import WebhookEvent

__all__ = [
    "MarketBand",
    "MarketFeed",
    "EventReport",
    "CityScan",
    "PublicMetric",
    "PublicQuota",
    "PublicReport",
    "WaitlistEntry",
    "AIUsage",
    "Account",
    "AppUser",
    "TermsAcceptance",
    "AuthAttempt",
    "AuthToken",
    "InviteCode",
    "PlatformSetting",
    "Membership",
    "UserSession",
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
