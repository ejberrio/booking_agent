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


# --- Conector de Channel Manager (feature 002) ---


class Provider(str, enum.Enum):
    beds24 = "beds24"


class ConnectionStatus(str, enum.Enum):
    unconfigured = "unconfigured"
    connected = "connected"
    invalid = "invalid"


class SyncDirection(str, enum.Enum):
    inbound = "inbound"  # import: remoto -> local
    outbound = "outbound"  # publish: local -> remoto


class SyncStatus(str, enum.Enum):
    running = "running"
    success = "success"
    partial = "partial"
    error = "error"


class SyncIssueKind(str, enum.Enum):
    comm_error = "comm_error"
    auth_error = "auth_error"
    price_discrepancy = "price_discrepancy"
    write_unverified = "write_unverified"
    rate_limited = "rate_limited"


class IssueStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


# --- Motor de precios (feature 003) ---


class PromotionAction(str, enum.Enum):
    created = "created"
    updated = "updated"
    deleted = "deleted"
