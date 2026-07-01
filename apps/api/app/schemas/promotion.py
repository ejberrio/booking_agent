"""Objetos de valor transitorios para promociones vía oferta (feature 011)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class PromotionPreview:
    """Propuesta de una promoción antes de confirmar (no se aplica nada)."""

    offer_id: int
    first_night: date
    last_night: date
    name: str
    base_price: Decimal | None
    price: Decimal
    discount_pct: Decimal | None
    saving: Decimal | None
    min_nights: int | None
    warnings: list[str] = field(default_factory=list)
    valid: bool = True
    reason: str | None = None
    fingerprint: str = ""


@dataclass
class PromotionView:
    """Una promoción existente para listar."""

    id: int
    name: str
    offer_id: int | None
    first_night: date
    last_night: date
    base_price: Decimal | None
    price: Decimal
    discount_pct: Decimal | None
    saving: Decimal | None
    min_nights: int | None
    status: str  # "published" | "sync_error" | "retired"
    published: bool


@dataclass
class PromotionApplyResult:
    id: int | None
    status: str  # "published" | "sync_error"
    external_id: int | None = None
    published: bool = False
    issue: str | None = None


def promotion_fingerprint(
    offer_id: int, first_night: date, last_night: date, price: Decimal, base_price: Decimal | None
) -> str:
    """Huella para detectar cambios entre preview y apply (patrón de precios)."""
    raw = f"{offer_id}|{first_night.isoformat()}|{last_night.isoformat()}|{price}|{base_price}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
