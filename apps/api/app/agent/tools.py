"""Registro de herramientas del agente y ejecución (lectura, propuesta, aplicación).

Las herramientas de lectura se ejecutan; las de escritura (`propose_*`) construyen
una propuesta (sin aplicar). `apply_proposal` aplica una propuesta confirmada vía
los servicios de la feature 003, con origen=chat.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentAction
from app.models.enums import ChangeOrigin, PromotionType
from app.models.pricing import Promotion
from app.schemas.pricing import RangeSelection
from app.services import pricing_app_service, promotion_service

REINFORCE_DAYS = 14
REINFORCE_VARIATION = Decimal("0.25")


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    is_write: bool


@dataclass
class Proposal:
    tool: str
    arguments: dict
    preview: dict
    fingerprint: str | None
    summary: str
    reinforced: bool


@dataclass
class ApplyOutcome:
    status: str  # "applied" | "stale"
    summary: str
    applied_ref: str | None = None


_INT = {"type": "integer"}
_STR = {"type": "string"}
_NUM = {"type": "number"}

READ_TOOLS = [
    ToolSpec(
        "get_calendar",
        "Consulta precio base, efectivo, disponibilidad y promociones por día en un rango.",
        {
            "type": "object",
            "properties": {"unit_type_id": _INT, "date_from": _STR, "date_to": _STR},
            "required": ["unit_type_id", "date_from", "date_to"],
        },
        False,
    ),
    ToolSpec(
        "get_history",
        "Historial de cambios de precio de una unidad en un rango.",
        {
            "type": "object",
            "properties": {"unit_type_id": _INT, "date_from": _STR, "date_to": _STR},
            "required": ["unit_type_id", "date_from", "date_to"],
        },
        False,
    ),
    ToolSpec(
        "get_suggestions",
        "Lista las sugerencias de precio vigentes (propuestas), con rango de fechas opcional.",
        {"type": "object", "properties": {"date_from": _STR, "date_to": _STR}},
        False,
    ),
    ToolSpec(
        "get_bookings",
        "Lista las reservas confirmadas que se solapan con un rango de fechas "
        "(con llegada/salida y número de noches). Úsala para preguntas sobre reservas.",
        {
            "type": "object",
            "properties": {"date_from": _STR, "date_to": _STR},
            "required": ["date_from", "date_to"],
        },
        False,
    ),
]

WRITE_TOOLS = [
    ToolSpec(
        "propose_set_day",
        "Propone fijar el precio de un día específico (no aplica hasta confirmar).",
        {
            "type": "object",
            "properties": {"unit_type_id": _INT, "day": _STR, "price": _NUM},
            "required": ["unit_type_id", "day", "price"],
        },
        True,
    ),
    ToolSpec(
        "propose_set_range",
        "Propone fijar un precio en un rango, con filtro opcional por días de semana (0=lun..6=dom).",
        {
            "type": "object",
            "properties": {
                "unit_type_id": _INT,
                "date_from": _STR,
                "date_to": _STR,
                "weekdays": {"type": "array", "items": _INT},
                "price": _NUM,
            },
            "required": ["unit_type_id", "date_from", "date_to", "price"],
        },
        True,
    ),
    ToolSpec(
        "propose_create_promotion",
        "Propone crear una promoción (porcentaje o monto) en un rango.",
        {
            "type": "object",
            "properties": {
                "property_id": _INT,
                "name": _STR,
                "discount_type": {"type": "string", "enum": ["percent", "amount"]},
                "discount_value": _NUM,
                "start_date": _STR,
                "end_date": _STR,
            },
            "required": ["property_id", "name", "discount_type", "discount_value", "start_date", "end_date"],
        },
        True,
    ),
    ToolSpec(
        "propose_delete_promotion",
        "Propone eliminar una promoción por id.",
        {"type": "object", "properties": {"promotion_id": _INT}, "required": ["promotion_id"]},
        True,
    ),
    ToolSpec(
        "propose_rollback",
        "Propone revertir un cambio de precio por id de cambio.",
        {"type": "object", "properties": {"change_id": _INT}, "required": ["change_id"]},
        True,
    ),
]

CONTROL_TOOLS = [
    ToolSpec("confirm_pending", "Confirma y aplica la propuesta pendiente.", {"type": "object", "properties": {}}, True),
    ToolSpec("cancel_pending", "Cancela la propuesta pendiente.", {"type": "object", "properties": {}}, True),
]

ALL_TOOLS = {t.name: t for t in READ_TOOLS + WRITE_TOOLS + CONTROL_TOOLS}


def openai_tools(include_control: bool) -> list[dict]:
    specs = READ_TOOLS + WRITE_TOOLS + (CONTROL_TOOLS if include_control else [])
    return [
        {"type": "function", "function": {"name": s.name, "description": s.description, "parameters": s.parameters}}
        for s in specs
    ]


# ---------- ejecución ----------


async def exec_read(session: AsyncSession, name: str, args: dict) -> Any:
    if name == "get_suggestions":
        from app.models.enums import SuggestionStatus
        from app.services import intelligence_service

        df_s = args.get("date_from")
        dt_s = args.get("date_to")
        out = []
        for s in await intelligence_service.list_suggestions(
            session, status=SuggestionStatus.proposed
        ):
            if df_s and s.date_to.isoformat() < df_s:
                continue
            if dt_s and s.date_from.isoformat() > dt_s:
                continue
            out.append(
                {
                    "id": s.id,
                    "date_from": s.date_from.isoformat(),
                    "date_to": s.date_to.isoformat(),
                    "price": str(s.suggested_price),
                    "rationale": s.rationale,
                }
            )
        return out

    if name == "get_bookings":
        from sqlalchemy import select

        from app.models.booking import Booking
        from app.models.enums import BookingStatus

        df_b = date.fromisoformat(args["date_from"])
        dt_b = date.fromisoformat(args["date_to"])
        res = await session.execute(
            select(Booking)
            .where(
                Booking.status == BookingStatus.confirmed,
                Booking.check_in <= dt_b,
                Booking.check_out > df_b,
            )
            .order_by(Booking.check_in)
        )
        return [
            {
                "external_ref": b.external_ref,
                "check_in": b.check_in.isoformat(),
                "check_out": b.check_out.isoformat(),
                "nights": (b.check_out - b.check_in).days,
            }
            for b in res.scalars()
        ]

    df = date.fromisoformat(args["date_from"])
    dt = date.fromisoformat(args["date_to"])
    uid = int(args["unit_type_id"])
    if name == "get_calendar":
        views = await pricing_app_service.get_calendar(session, uid, df, dt)
        return [
            {
                "date": v.date.isoformat(),
                "base": str(v.base_price) if v.base_price is not None else None,
                "effective": str(v.effective_price) if v.effective_price is not None else None,
                "available": v.available,
                "promotions": v.promotions,
            }
            for v in views
        ]
    if name == "get_history":
        logs = await pricing_app_service.history(session, uid, df, dt)
        return [
            {"id": log.id, "date": log.date.isoformat(), "old": str(log.old_price) if log.old_price else None, "new": str(log.new_price), "origin": log.origin.value}
            for log in logs
        ]
    raise ValueError(f"herramienta de lectura desconocida: {name}")


def _selection(args: dict) -> RangeSelection:
    return RangeSelection(
        date.fromisoformat(args["date_from"]),
        date.fromisoformat(args["date_to"]),
        weekdays=args.get("weekdays"),
    )


def _variation_exceeds(items, new_price: Decimal) -> bool:
    for it in items:
        old = it.old_price
        if old and old > 0 and abs(new_price - old) / old > REINFORCE_VARIATION:
            return True
    return False


async def build_proposal(session: AsyncSession, name: str, args: dict) -> Proposal:
    if name in ("propose_set_range", "propose_set_day"):
        uid = int(args["unit_type_id"])
        price = Decimal(str(args["price"]))
        if price <= 0:
            raise ValueError(
                "precio inválido (debe ser > 0). Para un cambio relativo (p. ej. 'sube 15%'), "
                "primero consulta el precio actual con get_calendar y propón el valor ABSOLUTO "
                "calculado (precio_actual × (1 + porcentaje/100))."
            )
        if name == "propose_set_day":
            sel = RangeSelection(date.fromisoformat(args["day"]), date.fromisoformat(args["day"]))
        else:
            sel = _selection(args)
        preview = await pricing_app_service.preview_range(
            session, unit_type_id=uid, selection=sel, price=price
        )
        reinforced = len(preview.items) > REINFORCE_DAYS or _variation_exceeds(preview.items, price)
        nota = " ⚠️ Es un cambio grande." if reinforced else ""
        summary = (
            f"Propongo fijar {price} COP en {preview.valid_count} día(s)"
            f"{' (' + str(preview.invalid_count) + ' fuera de límites)' if preview.invalid_count else ''}."
            f"{nota} ¿Confirmas?"
        )
        preview_dict = {
            "days": [
                {"date": i.date.isoformat(), "old": str(i.old_price) if i.old_price else None, "new": str(i.new_price), "valid": i.valid}
                for i in preview.items
            ],
            "valid_count": preview.valid_count,
            "invalid_count": preview.invalid_count,
        }
        return Proposal(name, args, preview_dict, preview.fingerprint, summary, reinforced)

    if name == "propose_create_promotion":
        days = (date.fromisoformat(args["end_date"]) - date.fromisoformat(args["start_date"])).days + 1
        reinforced = days > REINFORCE_DAYS
        summary = (
            f"Propongo crear la promoción '{args['name']}' ({args['discount_value']} "
            f"{args['discount_type']}) del {args['start_date']} al {args['end_date']}. ¿Confirmas?"
        )
        return Proposal(name, args, {"days": days}, None, summary, reinforced)

    if name == "propose_delete_promotion":
        return Proposal(name, args, {}, None, f"Propongo eliminar la promoción {args['promotion_id']}. ¿Confirmas?", False)

    if name == "propose_rollback":
        return Proposal(name, args, {}, None, f"Propongo revertir el cambio {args['change_id']}. ¿Confirmas?", False)

    raise ValueError(f"herramienta de escritura desconocida: {name}")


async def apply_proposal(
    session: AsyncSession, channel, action: AgentAction, message_id: int | None
) -> ApplyOutcome:
    args = action.arguments
    tool = action.tool

    if tool in ("propose_set_range", "propose_set_day"):
        uid = int(args["unit_type_id"])
        price = Decimal(str(args["price"]))
        if tool == "propose_set_day":
            sel = RangeSelection(date.fromisoformat(args["day"]), date.fromisoformat(args["day"]))
        else:
            sel = _selection(args)
        res = await pricing_app_service.apply_range(
            session,
            channel,
            unit_type_id=uid,
            selection=sel,
            price=price,
            fingerprint=action.fingerprint or "",
            origin=ChangeOrigin.chat,
            message_id=message_id,
        )
        if res.stale:
            return ApplyOutcome("stale", "El estado cambió desde la propuesta; vuelvo a proponer.")
        return ApplyOutcome(
            "applied",
            f"Listo: apliqué {len(res.applied_days)} día(s) y publiqué el precio efectivo.",
            f"applied_days={len(res.applied_days)}",
        )

    if tool == "propose_create_promotion":
        promo = await promotion_service.create_promotion(
            session,
            channel,
            property_id=int(args["property_id"]),
            name=args["name"],
            discount_type=PromotionType(args["discount_type"]),
            discount_value=Decimal(str(args["discount_value"])),
            start_date=date.fromisoformat(args["start_date"]),
            end_date=date.fromisoformat(args["end_date"]),
            origin=ChangeOrigin.chat,
        )
        return ApplyOutcome("applied", f"Promoción '{promo.name}' creada y aplicada.", f"promotion_id={promo.id}")

    if tool == "propose_delete_promotion":
        await promotion_service.delete_promotion(
            session, channel, int(args["promotion_id"]), origin=ChangeOrigin.chat
        )
        return ApplyOutcome("applied", "Promoción eliminada.", None)

    if tool == "propose_rollback":
        await pricing_app_service.rollback_and_publish(
            session, channel, int(args["change_id"]), confirm=True
        )
        return ApplyOutcome("applied", "Cambio revertido y publicado.", None)

    raise ValueError(f"no sé aplicar: {tool}")


async def get_promotion(session: AsyncSession, promotion_id: int) -> Promotion | None:
    return await session.get(Promotion, promotion_id)
