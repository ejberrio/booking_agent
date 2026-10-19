"""Registro de herramientas del agente y ejecución (lectura, propuesta, aplicación).

Las herramientas de lectura se ejecutan; las de escritura (`propose_*`) construyen
una propuesta (sin aplicar). `apply_proposal` aplica una propuesta confirmada vía
los servicios de la feature 003, con origen=chat.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.sync import get_adapter
from app.models.agent import AgentAction
from app.models.audit import PriceChangeLog
from app.models.enums import ChangeOrigin, PromotionType
from app.models.pricing import Promotion
from app.models.property import UnitType
from app.schemas.pricing import RangeSelection
from app.services import (
    availability_service,
    channel_pricing_service,
    offer_promotion_service,
    pricing_app_service,
    promotion_service,
)

REINFORCE_DAYS = 14
REINFORCE_VARIATION = Decimal("0.25")


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    is_write: bool
    # Feature 032: alias y herramientas viejas que siguen funcionando pero no se ofrecen
    # al modelo (confundían: precio único por rango, promociones legacy).
    hidden: bool = False


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
        "get_offer_promotions",
        "Lista las promociones de precio (ofertas con descuento sobre fechas) de una unidad: "
        "nombre, fechas, precio con descuento, ahorro y estado. Úsala para '¿qué promociones tengo?'.",
        {"type": "object", "properties": {"unit_type_id": _INT}, "required": ["unit_type_id"]},
        False,
    ),
    ToolSpec(
        "get_channel_offsets",
        "Ajuste de precio por canal vigente (offset %). Devuelve por canal: offset_pct "
        "(null = sin ajuste), supported (si es configurable) y si está activo. Úsala para "
        "preguntas de precio por canal y ANTES de proponer precios si podría haber ajustes.",
        {"type": "object", "properties": {}},
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
        "Lista las sugerencias de precio PENDIENTES (id, unidad, fechas, precio actual y "
        "sugerido, dirección up/down, noches vendibles y ocupadas, motivo corto). Filtros "
        "opcionales: unit_type_id, date_from, date_to, direction (up|down). Úsala antes de "
        "aplicar o rechazar sugerencias.",
        {
            "type": "object",
            "properties": {
                "unit_type_id": _INT,
                "date_from": _STR,
                "date_to": _STR,
                "direction": {"type": "string", "enum": ["up", "down"]},
            },
        },
        False,
    ),
    ToolSpec(
        "get_bookings",
        "Lista las reservas confirmadas que se solapan con un rango de fechas "
        "(con canal de origen, llegada/salida y número de noches). Úsala para preguntas "
        "sobre reservas; filtra por canal con 'channel' (booking|airbnb|direct) si el "
        "host pregunta por un canal específico.",
        {
            "type": "object",
            "properties": {
                "date_from": _STR,
                "date_to": _STR,
                "channel": {"type": "string", "enum": ["booking", "airbnb", "direct"]},
            },
            "required": ["date_from", "date_to"],
        },
        False,
    ),
    ToolSpec(
        "get_events",
        "Eventos ya conocidos en la zona de la propiedad (su municipio, el área metropolitana "
        "y los festivos/puentes) entre dos fechas: nombre, fechas, recinto, importancia y "
        "origen. Sin costo. Úsala para '¿qué eventos hay…?' y para explicar sugerencias.",
        {
            "type": "object",
            "properties": {"date_from": _STR, "date_to": _STR},
            "required": ["date_from", "date_to"],
        },
        False,
    ),
    ToolSpec(
        "report_event",
        "El host reporta un evento que NO aparece en get_events (llama a get_events antes). "
        "StayLever lo verifica con una búsqueda: si se confirma, lo agrega para su zona y "
        "recalcula sus sugerencias de esas fechas; si no, queda como nota en su calendario. "
        "Máximo 3 por día. No cambia precios. Pide nombre y fecha si faltan.",
        {
            "type": "object",
            "properties": {
                "name": _STR, "start_date": _STR, "end_date": _STR, "venue": _STR,
            },
            "required": ["name", "start_date"],
        },
        False,
    ),
    ToolSpec(
        "sync_calendar",
        "Sincroniza AHORA con el Channel Manager: importa reservas nuevas, cancelaciones, "
        "cambios de fechas, precios y disponibilidad. Úsala cuando el host diga que algo "
        "cambió en Booking/Airbnb (p. ej. una cancelación) y aún no se refleje en la app. "
        "Es solo lectura del canal (no publica nada).",
        {"type": "object", "properties": {}},
        False,
    ),
]

WRITE_TOOLS = [
    ToolSpec(
        "propose_price_change",
        "Propone cambiar el PRECIO BASE de varias noches en UNA sola propuesta. mode: 'set' "
        "(fijar value como precio), 'percent' (subir/bajar value %, p. ej. 10 o -15) o "
        "'amount' (sumar/restar value en la moneda). Selecciona noches con date_from/date_to "
        "y weekdays opcional (0=lun..6=dom; fin de semana = noches de viernes y sábado [4,5]) "
        "o con 'dates' (lista de fechas sueltas). El servidor calcula cada noche y omite "
        "pasadas, reservadas, bloqueadas, sin precio y fuera de límites. round_to opcional "
        "(p. ej. 1000). Para DESCUENTOS o PROMOCIONES usa 'propose_discount'.",
        {
            "type": "object",
            "properties": {
                "unit_type_id": _INT,
                "mode": {"type": "string", "enum": ["set", "percent", "amount"]},
                "value": _NUM,
                "date_from": _STR,
                "date_to": _STR,
                "weekdays": {"type": "array", "items": _INT},
                "dates": {"type": "array", "items": _STR},
                "round_to": _INT,
            },
            "required": ["unit_type_id", "mode", "value"],
        },
        True,
    ),
    ToolSpec(
        "propose_apply_suggestions",
        "Propone APLICAR sugerencias pendientes en bloque, con las mismas reglas del botón "
        "Aplicar (subidas al precio base; bajadas como promoción con piso del precio mínimo). "
        "Pasa suggestion_ids o filtros (date_from, date_to, unit_type_id, direction up|down). "
        "Una sola confirmación.",
        {
            "type": "object",
            "properties": {
                "suggestion_ids": {"type": "array", "items": _INT},
                "unit_type_id": _INT,
                "date_from": _STR,
                "date_to": _STR,
                "direction": {"type": "string", "enum": ["up", "down"]},
            },
        },
        True,
    ),
    ToolSpec(
        "propose_reject_suggestions",
        "Propone RECHAZAR sugerencias pendientes en bloque (por suggestion_ids o filtros "
        "date_from, date_to, unit_type_id, direction). No cambia precios.",
        {
            "type": "object",
            "properties": {
                "suggestion_ids": {"type": "array", "items": _INT},
                "unit_type_id": _INT,
                "date_from": _STR,
                "date_to": _STR,
                "direction": {"type": "string", "enum": ["up", "down"]},
            },
        },
        True,
    ),
    ToolSpec(
        "propose_discount",
        "Propone un DESCUENTO publicado como promoción (el precio base no cambia): "
        "discount_pct (sobre el precio de CADA noche) o price (precio con descuento). Noches "
        "con date_from/date_to + weekdays opcional (p. ej. martes = [1]) o 'dates'. Opcionales: "
        "min_nights, channels_scope (['booking'] o ['airbnb']). El servidor respeta el precio "
        "mínimo, agrupa en promociones por tramos y muestra avisos de solapes y reservas. "
        "Para editar o retirar una promoción existente usa propose_offer_promotion / "
        "propose_retire_offer_promotion.",
        {
            "type": "object",
            "properties": {
                "unit_type_id": _INT,
                "name": _STR,
                "discount_pct": _NUM,
                "price": _NUM,
                "date_from": _STR,
                "date_to": _STR,
                "weekdays": {"type": "array", "items": _INT},
                "dates": {"type": "array", "items": _STR},
                "min_nights": _INT,
                "channels_scope": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["booking", "airbnb"]},
                },
            },
            "required": ["unit_type_id", "name"],
        },
        True,
    ),
    ToolSpec(
        "propose_set_day",
        "Propone fijar el precio de un día específico (no aplica hasta confirmar).",
        {
            "type": "object",
            "properties": {"unit_type_id": _INT, "day": _STR, "price": _NUM},
            "required": ["unit_type_id", "day", "price"],
        },
        True,
        hidden=True,
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
        hidden=True,
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
        hidden=True,
    ),
    ToolSpec(
        "propose_delete_promotion",
        "Propone eliminar una promoción por id.",
        {"type": "object", "properties": {"promotion_id": _INT}, "required": ["promotion_id"]},
        True,
        hidden=True,
    ),
    ToolSpec(
        "propose_offer_promotion",
        "Propone crear o editar una PROMOCIÓN DE PRECIO: una oferta con nombre y descuento sobre "
        "un rango de fechas, que se publica al Channel Manager (Beds24) sobre la oferta designada. "
        "Indica descuento como porcentaje (discount_pct) o precio absoluto (price). No aplica hasta "
        "confirmar. Para editar una existente, incluye promotion_id.",
        {
            "type": "object",
            "properties": {
                "unit_type_id": _INT,
                "name": _STR,
                "first_night": _STR,
                "last_night": _STR,
                "discount_pct": _NUM,
                "price": _NUM,
                "min_nights": _INT,
                "promotion_id": _INT,
                "channels_scope": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["booking", "airbnb"]},
                },
            },
            "required": ["unit_type_id", "name", "first_night", "last_night"],
        },
        True,
    ),
    ToolSpec(
        "propose_channel_offset",
        "Propone un AJUSTE DE PRECIO POR CANAL (offset %): recargo/descuento porcentual del "
        "canal sobre el precio base (p. ej. Airbnb +8%). 0 = quitar el ajuste. No aplica hasta "
        "confirmar. Solo canales configurables (Booking vende al precio base).",
        {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "enum": ["booking", "airbnb"]},
                "offset_pct": _NUM,
            },
            "required": ["channel", "offset_pct"],
        },
        True,
    ),
    ToolSpec(
        "propose_retire_offer_promotion",
        "Propone retirar (dejar de aplicar) una promoción de precio por id. No aplica hasta confirmar.",
        {"type": "object", "properties": {"promotion_id": _INT}, "required": ["promotion_id"]},
        True,
    ),
    ToolSpec(
        "propose_rollback",
        "Propone revertir un cambio de precio por id de cambio.",
        {"type": "object", "properties": {"change_id": _INT}, "required": ["change_id"]},
        True,
    ),
    ToolSpec(
        "propose_block_availability",
        "Propone CERRAR (bloquear) la disponibilidad de un rango, con filtro opcional por días "
        "de semana (0=lun..6=dom). No aplica hasta confirmar; omite noches con reserva.",
        {
            "type": "object",
            "properties": {
                "unit_type_id": _INT,
                "date_from": _STR,
                "date_to": _STR,
                "weekdays": {"type": "array", "items": _INT},
            },
            "required": ["unit_type_id", "date_from", "date_to"],
        },
        True,
    ),
    ToolSpec(
        "propose_open_availability",
        "Propone REABRIR (abrir) la disponibilidad de un rango previamente bloqueado. No aplica "
        "hasta confirmar; no altera noches reservadas.",
        {
            "type": "object",
            "properties": {
                "unit_type_id": _INT,
                "date_from": _STR,
                "date_to": _STR,
                "weekdays": {"type": "array", "items": _INT},
            },
            "required": ["unit_type_id", "date_from", "date_to"],
        },
        True,
    ),
]

CONTROL_TOOLS = [
    ToolSpec("confirm_pending", "Confirma y aplica la propuesta pendiente.", {"type": "object", "properties": {}}, True),
    ToolSpec("cancel_pending", "Cancela la propuesta pendiente.", {"type": "object", "properties": {}}, True),
]

ALL_TOOLS = {t.name: t for t in READ_TOOLS + WRITE_TOOLS + CONTROL_TOOLS}


def openai_tools(include_control: bool) -> list[dict]:
    specs = [t for t in READ_TOOLS + WRITE_TOOLS if not t.hidden]
    specs += CONTROL_TOOLS if include_control else []
    return [
        {"type": "function", "function": {"name": s.name, "description": s.description, "parameters": s.parameters}}
        for s in specs
    ]


# ---------- ejecución ----------


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class UnitNotFound(ValueError):
    """Unidad inexistente o de otra cuenta (feature 026: mismo mensaje en ambos casos)."""


async def ensure_unit(session: AsyncSession, unit_type_id: Any) -> UnitType:
    """La unidad que pide el LLM debe ser de la cuenta de la conversación (principio VI)."""
    try:
        uid = int(unit_type_id)
    except (TypeError, ValueError):
        raise UnitNotFound("unit_type_id inválido") from None
    unit = await session.get(UnitType, uid)
    if unit is None:
        raise UnitNotFound(f"la unidad {uid} no existe")
    return unit


async def exec_read(session: AsyncSession, name: str, args: dict) -> Any:
    if "unit_type_id" in args and args["unit_type_id"] is not None:
        try:
            await ensure_unit(session, args["unit_type_id"])
        except UnitNotFound as exc:
            return {"error": str(exc)}
    return await _exec_read(session, name, args)


async def _exec_read(session: AsyncSession, name: str, args: dict) -> Any:
    if name == "get_offer_promotions":
        promos = await offer_promotion_service.list_promotions(session, int(args["unit_type_id"]))
        return [
            {
                "id": p.id,
                "name": p.name,
                "first_night": p.first_night.isoformat(),
                "last_night": p.last_night.isoformat(),
                "price": str(p.price),
                "base_price": str(p.base_price) if p.base_price is not None else None,
                "saving": str(p.saving) if p.saving is not None else None,
                "discount_pct": str(p.discount_pct) if p.discount_pct is not None else None,
                "min_nights": p.min_nights,
                "status": p.status,
            }
            for p in promos
        ]
    if name == "get_channel_offsets":
        adapter = get_adapter(session)
        try:
            return await channel_pricing_service.get_offsets(session, adapter)
        finally:
            await adapter.aclose()

    if name == "get_suggestions":
        return [
            {
                "id": v.suggestion.id,
                "unit_type_id": v.suggestion.unit_type_id,
                "date_from": v.suggestion.date_from.isoformat(),
                "date_to": v.suggestion.date_to.isoformat(),
                "current_price": str(cur) if cur is not None else None,
                "suggested_price": str(v.suggestion.suggested_price),
                "direction": direction,
                "sellable_nights": len(v.nights),
                "occupied_nights": v.occupied_count,
                "reason": ((v.suggestion.rationale or {}).get("text") or "")[:160],
            }
            for v, cur, direction in await _pending_suggestions(session, args)
        ]

    if name == "get_events":
        from app.services import event_report_service

        return await event_report_service.list_events(
            session, date.fromisoformat(args["date_from"]), date.fromisoformat(args["date_to"])
        )

    if name == "report_event":
        from app.services import event_report_service

        try:
            res = await event_report_service.report_metered(
                session, name=str(args.get("name") or ""),
                start_date=date.fromisoformat(args["start_date"]),
                end_date=date.fromisoformat(args["end_date"]) if args.get("end_date") else None,
                venue=args.get("venue"),
            )
        except (event_report_service.ReportError, ValueError) as exc:
            return {"error": str(exc)}
        return {"status": res.status, "message": res.message, "event": res.event}

    if name == "sync_calendar":
        from app.services import sync_service

        adapter = get_adapter(session)
        try:
            today = date.today()
            run = await sync_service.import_remote(
                session, adapter, today, today + timedelta(days=365)
            )
            return {
                "status": run.status.value,
                "created": run.created_count,
                "updated": run.updated_count,
                "issues": run.issue_count,
            }
        finally:
            await adapter.aclose()

    if name == "get_bookings":
        from sqlalchemy import select

        from app.models.booking import Booking
        from app.models.enums import BookingStatus, ChannelKind

        df_b = date.fromisoformat(args["date_from"])
        dt_b = date.fromisoformat(args["date_to"])
        stmt = (
            select(Booking)
            .where(
                Booking.status == BookingStatus.confirmed,
                Booking.check_in <= dt_b,
                Booking.check_out > df_b,
            )
            .order_by(Booking.check_in)
        )
        if args.get("channel"):
            stmt = stmt.where(Booking.channel_kind == ChannelKind(args["channel"]))
        res = await session.execute(stmt)
        return [
            {
                "external_ref": b.external_ref,
                "channel": b.channel_kind.value,
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


# ---------- feature 032: lote con una sola confirmación ----------

MAX_SUGGESTIONS = 100

_SUMMARY = {
    "price": {
        "es": "Propongo cambiar el precio de {n} noche(s) en {t} tramo(s){skip}.{big} ¿Confirmas?",
        "en": "I propose changing the price of {n} night(s) in {t} block(s){skip}.{big} Do you confirm?",
        "pt": "Proponho mudar o preço de {n} noite(s) em {t} trecho(s){skip}.{big} Você confirma?",
    },
    "discount": {
        "es": "Propongo un descuento en {n} noche(s), publicado como {t} promoción(es){skip}.{big} ¿Confirmas?",
        "en": "I propose a discount on {n} night(s), published as {t} promotion(s){skip}.{big} Do you confirm?",
        "pt": "Proponho um desconto em {n} noite(s), publicado como {t} promoção(ões){skip}.{big} Você confirma?",
    },
    "apply_suggestions": {
        "es": "Propongo aplicar {s} sugerencia(s): {n} noche(s){skip}.{big} ¿Confirmas?",
        "en": "I propose applying {s} suggestion(s): {n} night(s){skip}.{big} Do you confirm?",
        "pt": "Proponho aplicar {s} sugestão(ões): {n} noite(s){skip}.{big} Você confirma?",
    },
    "reject_suggestions": {
        "es": "Propongo rechazar {s} sugerencia(s). No cambia ningún precio. ¿Confirmas?",
        "en": "I propose rejecting {s} suggestion(s). No price changes. Do you confirm?",
        "pt": "Proponho rejeitar {s} sugestão(ões). Nenhum preço muda. Você confirma?",
    },
}
_SKIP = {"es": " ({k} omitida(s))", "en": " ({k} skipped)", "pt": " ({k} omitida(s))"}
_BIG_TXT = {"es": " ⚠️ Es un cambio grande.", "en": " ⚠️ This is a big change.", "pt": " ⚠️ É uma mudança grande."}
_DONE = {
    "price": {
        "es": "Listo: cambié {a} noche(s) y publiqué los precios{f}.",
        "en": "Done: I changed {a} night(s) and published the prices{f}.",
        "pt": "Pronto: mudei {a} noite(s) e publiquei os preços{f}.",
    },
    "discount": {
        "es": "Listo: publiqué {p} promoción(es) para {a} noche(s){f}.",
        "en": "Done: I published {p} promotion(s) for {a} night(s){f}.",
        "pt": "Pronto: publiquei {p} promoção(ões) para {a} noite(s){f}.",
    },
    "apply_suggestions": {
        "es": "Listo: apliqué {s} sugerencia(s) ({a} noche(s)){f}.",
        "en": "Done: I applied {s} suggestion(s) ({a} night(s)){f}.",
        "pt": "Pronto: apliquei {s} sugestão(ões) ({a} noite(s)){f}.",
    },
    "reject_suggestions": {
        "es": "Listo: rechacé {s} sugerencia(s).",
        "en": "Done: I rejected {s} suggestion(s).",
        "pt": "Pronto: rejeitei {s} sugestão(ões).",
    },
}
_FAILED = {"es": "; {x} noche(s) fallaron y quedaron igual", "en": "; {x} night(s) failed and stayed the same", "pt": "; {x} noite(s) falharam e ficaram iguais"}
_STALE = {
    "es": "El estado cambió desde la propuesta; vuelvo a proponer.",
    "en": "El estado cambió desde la propuesta; vuelvo a proponer.",
    "pt": "El estado cambió desde la propuesta; vuelvo a proponer.",
}


def _lang(language: str) -> str:
    return language if language in ("es", "en", "pt") else "es"


def summary_for(kind: str, language: str, **v) -> str:
    lang = _lang(language)
    skip = _SKIP[lang].format(k=v["k"]) if v.get("k") else ""
    big = _BIG_TXT[lang] if v.get("big") else ""
    return _SUMMARY[kind][lang].format(skip=skip, big=big, **{k: x for k, x in v.items() if k not in ("k", "big")})


def done_for(kind: str, language: str, **v) -> str:
    lang = _lang(language)
    f = _FAILED[lang].format(x=v["x"]) if v.get("x") else ""
    return _DONE[kind][lang].format(f=f, **{k: x for k, x in v.items() if k != "x"})


def _d(value) -> date | None:
    return date.fromisoformat(value) if value else None


def _dates(value) -> list[date] | None:
    return [date.fromisoformat(x) for x in value] if value else None


def _rows(tramos, *, note: str | None = None) -> list[dict]:
    return [
        {
            "from": t[0].date.isoformat(),
            "to": t[-1].date.isoformat(),
            "nights": len(t),
            "old": str(t[0].old) if t[0].old is not None else None,
            "new": str(t[0].new) if t[0].new is not None else None,
            "note": note,
        }
        for t in tramos
    ]


def _price_params(args: dict) -> dict:
    return {
        "unit_type_id": int(args["unit_type_id"]),
        "mode": str(args.get("mode") or "set"),
        "value": Decimal(str(args.get("value", 0))),
        "date_from": _d(args.get("date_from")),
        "date_to": _d(args.get("date_to")),
        "weekdays": args.get("weekdays") or None,
        "dates": _dates(args.get("dates")),
        "round_to": int(args["round_to"]) if args.get("round_to") else None,
    }


def _discount_params(args: dict) -> dict:
    return {
        "unit_type_id": int(args["unit_type_id"]),
        "name": str(args.get("name") or "Descuento")[:100],
        "discount_pct": Decimal(str(args["discount_pct"])) if args.get("discount_pct") is not None else None,
        "price": Decimal(str(args["price"])) if args.get("price") is not None else None,
        "date_from": _d(args.get("date_from")),
        "date_to": _d(args.get("date_to")),
        "weekdays": args.get("weekdays") or None,
        "dates": _dates(args.get("dates")),
        "min_nights": int(args["min_nights"]) if args.get("min_nights") else None,
        "channels_scope": args.get("channels_scope") or None,
    }


async def _pending_suggestions(session: AsyncSession, args: dict):
    """Sugerencias pendientes (filtro automático por cuenta) con precio actual y dirección."""
    from app.services import suggestion_batch

    uid = args.get("unit_type_id")
    views = await suggestion_batch.pending_views(
        session, unit_type_id=int(uid) if uid is not None else None
    )
    ids = args.get("suggestion_ids")
    if ids:
        wanted = {_int_or_zero(i) for i in ids}
        found = {v.suggestion.id for v in views}
        missing = sorted(wanted - found)
        if missing:
            raise ValueError(f"las sugerencias {missing} no existen o ya no están pendientes")
        views = [v for v in views if v.suggestion.id in wanted]
    df, dt = _d(args.get("date_from")), _d(args.get("date_to"))
    out = []
    for v in views:
        s = v.suggestion
        if df and s.date_to < df or dt and s.date_from > dt:
            continue
        cur = next((n.current_price for n in v.nights if n.current_price is not None), None)
        direction = "down" if cur is not None and s.suggested_price < cur else "up"
        if args.get("direction") and args["direction"] != direction:
            continue
        out.append((v, cur, direction))
    return out


async def _currency(session: AsyncSession, unit_type_id: int | None) -> str:
    from app.models.property import Property

    if unit_type_id is None:
        return "COP"
    unit = await session.get(UnitType, unit_type_id)
    prop = await session.get(Property, unit.property_id) if unit else None
    return prop.currency if prop else "COP"


async def _build_bulk(session: AsyncSession, name: str, args: dict, language: str) -> Proposal:
    from app.services import bulk_service, suggestion_batch

    try:
        if name == "propose_price_change":
            plan = await bulk_service.plan_price_change(session, **_price_params(args))
            tramos = plan.tramos()
            if not tramos:
                raise ValueError(
                    "ninguna noche cambia (todas omitidas: "
                    + ", ".join(f"{k}: {n}" for k, n in plan.skipped.items()) + ")."
                )
            big = len(plan.valid) > REINFORCE_DAYS or any(
                n.old and abs(n.new - n.old) / n.old > REINFORCE_VARIATION for n in plan.valid
            )
            preview = {
                "kind": "price",
                "rows": _rows(tramos),
                "totals": {"affected": len(plan.valid), "skipped": plan.skipped},
                "warnings": [],
                "currency": plan.currency,
            }
            summary = summary_for("price", language, n=len(plan.valid), t=len(tramos),
                                  k=sum(plan.skipped.values()), big=big)
            return Proposal(name, args, preview, plan.fingerprint, summary, big)

        if name == "propose_discount":
            adapter = get_adapter(session)
            try:
                plan = await bulk_service.plan_discount(session, adapter, **_discount_params(args))
            finally:
                await adapter.aclose()
            tramos = plan.tramos()
            if not tramos:
                raise ValueError(
                    "ninguna noche recibe el descuento (omitidas: "
                    + ", ".join(f"{k}: {n}" for k, n in plan.skipped.items()) + ")."
                )
            big = len(plan.valid) > REINFORCE_DAYS
            preview = {
                "kind": "discount",
                "rows": [
                    {**r, "note": f"-{t[0].pct}%"} for r, t in zip(_rows(tramos), tramos, strict=True)
                ],
                "totals": {"affected": len(plan.valid), "skipped": plan.skipped},
                "warnings": plan.warnings,
                "currency": plan.currency,
            }
            summary = summary_for("discount", language, n=len(plan.valid), t=len(tramos),
                                  k=sum(plan.skipped.values()), big=big)
            return Proposal(name, args, preview, plan.fingerprint, summary, big)
    except bulk_service.BulkError as exc:
        raise ValueError(str(exc)) from exc

    found = await _pending_suggestions(session, args)
    if not found:
        raise ValueError("no hay sugerencias pendientes que coincidan con esos filtros.")
    if len(found) > MAX_SUGGESTIONS:
        raise ValueError(f"son {len(found)} sugerencias (máximo {MAX_SUGGESTIONS}); acota las fechas.")
    ids = [v.suggestion.id for v, _c, _d2 in found]
    currency = await _currency(session, found[0][0].suggestion.unit_type_id)
    if name == "propose_reject_suggestions":
        preview = {
            "kind": "reject_suggestions",
            "rows": [
                {"from": v.suggestion.date_from.isoformat(), "to": v.suggestion.date_to.isoformat(),
                 "nights": v.total_nights, "old": str(c) if c is not None else None,
                 "new": str(v.suggestion.suggested_price), "note": d}
                for v, c, d in found
            ],
            "totals": {"affected": len(ids), "skipped": {}},
            "warnings": [],
            "currency": currency,
        }
        args = {**args, "suggestion_ids": ids}
        summary = summary_for("reject_suggestions", language, s=len(ids))
        return Proposal(name, args, preview, None, summary, False)

    batch = await suggestion_batch.preview_batch(session, ids)
    valid = [i for i in batch.items if i.valid]
    if not valid:
        raise ValueError("ninguna noche de esas sugerencias se puede aplicar (ocupadas, pasadas o fuera de límites).")
    tramos: list[list] = []
    for it in valid:
        last = tramos[-1][-1] if tramos else None
        if (
            last is not None and last.date + timedelta(days=1) == it.date and last.mode == it.mode
            and last.old_price == it.old_price and last.new_price == it.new_price
            and last.promo_price == it.promo_price
        ):
            tramos[-1].append(it)
        else:
            tramos.append([it])
    rows = [
        {
            "from": t[0].date.isoformat(), "to": t[-1].date.isoformat(), "nights": len(t),
            "old": str(t[0].old_price) if t[0].old_price is not None else None,
            "new": str(t[0].promo_price if t[0].mode == "promotion" else t[0].new_price),
            "note": f"promo -{t[0].promo_pct}%" if t[0].mode == "promotion" else None,
        }
        for t in tramos
    ]
    skipped = dict(Counter(i.reason or "" for i in batch.items if not i.valid))
    warnings = [f"Se solapa con: {o}" for o in batch.overlaps]
    if any(i.clipped for i in valid):
        warnings.append("Algunas bajadas se recortaron por tu precio mínimo.")
    big = len(valid) > REINFORCE_DAYS
    preview = {
        "kind": "apply_suggestions",
        "rows": rows,
        "totals": {"affected": len(valid), "skipped": skipped},
        "warnings": warnings,
        "currency": currency,
    }
    args = {**args, "suggestion_ids": ids}
    summary = summary_for("apply_suggestions", language, s=len(ids), n=len(valid),
                          k=sum(skipped.values()), big=big)
    return Proposal(name, args, preview, batch.fingerprint, summary, big)


async def _apply_bulk(session: AsyncSession, channel, action: AgentAction, message_id, language: str):
    from app.services import bulk_service, intelligence_service, suggestion_batch

    args, tool = action.arguments, action.tool
    stale = ApplyOutcome("stale", _STALE[_lang(language)])
    if tool == "propose_price_change":
        rep = await bulk_service.apply_price_change(
            session, channel, fingerprint=action.fingerprint or "", origin=ChangeOrigin.chat,
            message_id=message_id, **_price_params(args),
        )
        if rep.stale:
            return stale
        return ApplyOutcome("applied", done_for("price", language, a=rep.applied, x=rep.failed),
                            f"price_change:{rep.applied}")
    if tool == "propose_discount":
        rep = await bulk_service.apply_discount(
            session, channel, fingerprint=action.fingerprint or "", origin=ChangeOrigin.chat,
            **_discount_params(args),
        )
        if rep.stale:
            return stale
        return ApplyOutcome(
            "applied", done_for("discount", language, p=len(rep.promotions), a=rep.applied, x=rep.failed),
            "promotions=" + ",".join(str(i) for i in rep.promotions),
        )
    ids = [int(i) for i in args.get("suggestion_ids") or []]
    if tool == "propose_reject_suggestions":
        done = 0
        for sid in ids:
            try:
                await intelligence_service.reject(session, sid)
                done += 1
            except (ValueError, LookupError):
                continue  # ya resuelta o inexistente: se omite
        return ApplyOutcome("applied", done_for("reject_suggestions", language, s=done), f"rejected:{done}")
    res = await suggestion_batch.apply_batch(session, channel, ids, action.fingerprint or "")
    if res.stale:
        return stale
    applied = sum(1 for st in res.suggestions.values() if st == "applied")
    return ApplyOutcome(
        "applied",
        done_for("apply_suggestions", language, s=applied, a=res.applied_count, x=res.failed_count),
        f"suggestions_applied:{applied}",
    )


BULK_TOOLS = {
    "propose_price_change",
    "propose_discount",
    "propose_apply_suggestions",
    "propose_reject_suggestions",
}


async def build_proposal(
    session: AsyncSession, name: str, args: dict, language: str = "es"
) -> Proposal:
    # Feature 026: todo identificador que elija el LLM debe ser de la cuenta de la
    # conversación; si no, "no existe" (ValueError → el agente lo explica y no propone).
    if "unit_type_id" in args and args["unit_type_id"] is not None:
        await ensure_unit(session, args["unit_type_id"])  # UnitNotFound es ValueError
    if args.get("promotion_id") is not None:
        if await session.get(Promotion, _int_or_zero(args["promotion_id"])) is None:
            raise ValueError(f"la promoción {args['promotion_id']} no existe")
    if name == "propose_rollback":
        if await session.get(PriceChangeLog, _int_or_zero(args.get("change_id"))) is None:
            raise ValueError(f"el cambio {args.get('change_id')} no existe")
    if name in BULK_TOOLS:
        return await _build_bulk(session, name, args, language)
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

    if name == "propose_offer_promotion":
        first = date.fromisoformat(args["first_night"])
        last = date.fromisoformat(args["last_night"])
        if last < first:
            raise ValueError("la última noche no puede ser anterior a la primera.")
        if last < date.today():
            raise ValueError("el rango de la promoción está en el pasado.")
        pct = args.get("discount_pct")
        price = args.get("price")
        if pct is None and price is None:
            raise ValueError("indica el descuento como porcentaje (discount_pct) o precio absoluto (price).")
        if pct is not None and not (0 < float(pct) < 100):
            raise ValueError("el porcentaje de descuento debe estar entre 0 y 100.")
        if price is not None and float(price) <= 0:
            raise ValueError("el precio con descuento debe ser mayor que 0.")
        desc = f"{pct}% de descuento" if pct is not None else f"precio {price}"
        mn = f", mínimo {args['min_nights']} noches" if args.get("min_nights") else ""
        scope = args.get("channels_scope")
        alcance = f" (solo {', '.join(scope)})" if scope else " (todos los canales)"
        verbo = "editar" if args.get("promotion_id") else "crear"
        reinforced = (last - first).days + 1 > REINFORCE_DAYS
        summary = (
            f"Propongo {verbo} la promoción '{args['name']}' ({desc}) del {first} al {last}{mn}{alcance}. ¿Confirmas?"
        )
        return Proposal(name, args, {"first_night": first.isoformat(), "last_night": last.isoformat()}, None, summary, reinforced)

    if name == "propose_channel_offset":
        adapter = get_adapter(session)
        try:
            prev = await channel_pricing_service.preview_offset(
                session, adapter, str(args["channel"]), Decimal(str(args["offset_pct"]))
            )
        except channel_pricing_service.ChannelOffsetError as exc:
            raise ValueError(str(exc)) from exc
        finally:
            await adapter.aclose()
        pct_txt = prev["new_pct"]
        example = prev["example"]
        extra = "".join(f" ⚠️ {w}" for w in prev["warnings"])
        summary = (
            f"Propongo ajustar el precio del canal {prev['channel']} a {pct_txt}% "
            f"(ej.: base {example['base']} → {example['effective']} COP).{extra} ¿Confirmas?"
        )
        return Proposal(name, args, prev, None, summary, False)

    if name == "propose_retire_offer_promotion":
        return Proposal(name, args, {}, None, f"Propongo retirar la promoción {args['promotion_id']} (dejará de aplicar el descuento). ¿Confirmas?", False)

    if name == "propose_rollback":
        return Proposal(name, args, {}, None, f"Propongo revertir el cambio {args['change_id']}. ¿Confirmas?", False)

    if name in ("propose_block_availability", "propose_open_availability"):
        uid = int(args["unit_type_id"])
        act = "block" if name == "propose_block_availability" else "open"
        prev = await availability_service.preview(
            session, unit_type_id=uid, selection=_selection(args), action=act
        )
        verbo = "bloquear" if act == "block" else "abrir"
        nota = " ⚠️ Es un cambio grande." if prev.reinforced else ""
        omit = f" ({prev.skipped_count} omitida(s))" if prev.skipped_count else ""
        summary = f"Propongo {verbo} {prev.affected_count} noche(s){omit}.{nota} ¿Confirmas?"
        preview_dict = {
            "action": act,
            "affected": prev.affected_count,
            "skipped": prev.skipped_count,
            "days": [
                {"date": i.date.isoformat(), "valid": i.valid, "reason": i.skip_reason}
                for i in prev.items
            ],
        }
        return Proposal(name, args, preview_dict, prev.fingerprint, summary, prev.reinforced)

    raise ValueError(f"herramienta de escritura desconocida: {name}")


async def apply_proposal(
    session: AsyncSession, channel, action: AgentAction, message_id: int | None,
    language: str = "es",
) -> ApplyOutcome:
    args = action.arguments
    tool = action.tool
    if tool in BULK_TOOLS:
        return await _apply_bulk(session, channel, action, message_id, language)

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

    if tool == "propose_offer_promotion":
        res = await offer_promotion_service.apply(
            session,
            channel,
            unit_type_id=int(args["unit_type_id"]),
            first_night=date.fromisoformat(args["first_night"]),
            last_night=date.fromisoformat(args["last_night"]),
            name=args["name"],
            discount_pct=Decimal(str(args["discount_pct"])) if args.get("discount_pct") is not None else None,
            price=Decimal(str(args["price"])) if args.get("price") is not None else None,
            min_nights=int(args["min_nights"]) if args.get("min_nights") else None,
            promotion_id=int(args["promotion_id"]) if args.get("promotion_id") else None,
            fingerprint=None,
            confirm_overlap=True,
            origin=ChangeOrigin.chat,
            channels_scope=args.get("channels_scope"),
        )
        if res.status == "sync_error":
            return ApplyOutcome("applied", f"Promoción guardada, pero falló la publicación: {res.issue}", f"promotion_id={res.id}")
        return ApplyOutcome("applied", "Promoción creada y publicada.", f"promotion_id={res.id}")

    if tool == "propose_channel_offset":
        res = await channel_pricing_service.apply_offset(
            session,
            channel,
            str(args["channel"]),
            Decimal(str(args["offset_pct"])),
            fingerprint=None,  # gate humano = confirmación del chat
            origin=ChangeOrigin.chat,
        )
        msg = f"Ajuste del canal {res['channel']} aplicado: {res['offset_pct']}%."
        if not res["verified"]:
            msg += f" ⚠️ No se pudo verificar en el Channel Manager: {res['issue']}"
        return ApplyOutcome("applied", msg, f"channel={res['channel']}")

    if tool == "propose_retire_offer_promotion":
        res = await offer_promotion_service.retire(
            session, channel, int(args["promotion_id"]), confirm=True, origin=ChangeOrigin.chat
        )
        return ApplyOutcome("applied", "Promoción retirada (deja de aplicar el descuento).", f"promotion_id={res.id}")

    if tool == "propose_rollback":
        await pricing_app_service.rollback_and_publish(
            session, channel, int(args["change_id"]), confirm=True
        )
        return ApplyOutcome("applied", "Cambio revertido y publicado.", None)

    if tool in ("propose_block_availability", "propose_open_availability"):
        uid = int(args["unit_type_id"])
        act = "block" if tool == "propose_block_availability" else "open"
        res = await availability_service.apply(
            session,
            channel,
            unit_type_id=uid,
            selection=_selection(args),
            action=act,
            fingerprint=action.fingerprint or "",
            origin=ChangeOrigin.chat,
            message_id=message_id,
        )
        if res.stale:
            return ApplyOutcome("stale", "El estado cambió desde la propuesta; vuelvo a proponer.")
        verbo = "bloqueé" if act == "block" else "reabrí"
        omit = f" ({len(res.skipped)} omitida(s))" if res.skipped else ""
        return ApplyOutcome(
            "applied",
            f"Listo: {verbo} {len(res.applied)} noche(s){omit} y publiqué la disponibilidad.",
            f"availability:{len(res.applied)}",
        )

    raise ValueError(f"no sé aplicar: {tool}")


async def get_promotion(session: AsyncSession, promotion_id: int) -> Promotion | None:
    return await session.get(Promotion, promotion_id)
