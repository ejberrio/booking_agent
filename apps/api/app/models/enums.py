import enum


class PropertyStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class ChannelKind(str, enum.Enum):
    booking = "booking"
    airbnb = "airbnb"
    direct = "direct"


class ChangeOrigin(str, enum.Enum):
    chat = "chat"
    manual = "manual"
    suggestion = "suggestion"
    rollback = "rollback"


class SuggestionStatus(str, enum.Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    applied = "applied"


class PromotionType(str, enum.Enum):
    percent = "percent"
    amount = "amount"


class PromotionStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class BookingStatus(str, enum.Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    pending = "pending"


class EventKind(str, enum.Enum):
    concert = "concert"
    fair = "fair"
    convention = "convention"
    holiday = "holiday"
    festival = "festival"
    other = "other"


class Relevance(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"
