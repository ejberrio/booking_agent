"""Informe gratis de la página pública (feature 030).

El visitante (sin cuenta) elige un municipio y su precio; el informe muestra los eventos de
los próximos 3 meses con el precio sugerido por el MISMO cálculo de la app
(`suggest_price_v2`). Gratis van los 3 más importantes; el resto, con cuenta.

Costos acotados:
- Los eventos son públicos por ciudad (`event`). Si la ciudad se buscó hace menos de
  `CACHE_DAYS` (escaneo diario o un informe anterior, ver `city_scan`), no se gasta nada.
- Si no, se busca UNA vez (búsqueda web + IA, como el escaneo diario) dentro de un
  presupuesto diario global de ciudades nuevas (`registration_open.city_budget`).
- Límite diario por visitante: HMAC de la IP con la fecha (no se guarda la IP).

Aislamiento (principio VI): aquí solo se leen `event` (datos públicos) y tablas de plataforma.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import digest
from app.core.config import settings
from app.domain import municipalities
from app.domain.municipalities import Municipality
from app.domain.suggestion import EventSignal, suggest_price_v2
from app.models.enums import Relevance
from app.models.market import Event
from app.models.mixins import _now
from app.models.public import CityScan, PublicMetric, PublicQuota, PublicReport, WaitlistEntry
from app.services.usage_service import local_today

log = logging.getLogger(__name__)

HORIZON_DAYS = 90  # lo que las agendas públicas suelen publicar (decisión del host)
FREE_EVENTS = 3
CACHE_DAYS = 7
REPORTS_PER_VISITOR_DAY = 10
WAITLIST_PER_VISITOR_DAY = 5
WEEKEND = (4, 5)  # noches de viernes y sábado
MAX_PRICE = Decimal("100000000")
_REL_ORDER = {Relevance.high: 0, Relevance.medium: 1, Relevance.low: 2}
LANGS = ("es", "en", "pt")

# Métricas (public_metric.key)
VISIT, REPORT, REPORT_CACHED, CITY_SEARCH = "visit", "report", "report_cached", "city_search"
SIGNUP_OPEN, SIGNUP_FROM_REPORT, WAITLIST = "signup_open", "signup_from_report", "waitlist"


class PublicError(Exception):
    def __init__(self, code: str, detail: str, status: int = 400):
        super().__init__(detail)
        self.code, self.detail, self.status = code, detail, status


# --------- medición y límites ---------


async def bump(session: AsyncSession, key: str, n: int = 1, day: date | None = None) -> None:
    day = day or local_today()
    row = await session.get(PublicMetric, (day, key))
    if row is None:
        session.add(PublicMetric(day=day, key=key, value=n))
    else:
        row.value += n
    await session.flush()


def visitor_id(ip: str | None, day: date | None = None) -> str:
    """HMAC(secreto, ip + día): sirve para el límite diario y no permite recuperar la IP."""
    day = day or local_today()
    msg = f"{(ip or 'unknown').strip()}|{day.isoformat()}".encode()
    return hmac.new(settings.secret_key.encode(), msg, hashlib.sha256).hexdigest()[:32]


async def _take(session: AsyncSession, visitor: str, kind: str, limit: int) -> None:
    day = local_today()
    row = await session.get(PublicQuota, (day, visitor, kind))
    if row is not None and row.count >= limit:
        raise PublicError("rate_limited", "Llegaste al límite de hoy. Vuelve mañana.", 429)
    if row is None:
        session.add(PublicQuota(day=day, visitor=visitor, kind=kind, count=1))
    else:
        row.count += 1
    await session.flush()


async def purge_old(session: AsyncSession, today: date | None = None) -> None:
    """Borra contadores de visitantes de días anteriores y la lista de espera de > 12 meses."""
    today = today or local_today()
    await session.execute(delete(PublicQuota).where(PublicQuota.day < today))
    cutoff = _now() - timedelta(days=365)
    await session.execute(delete(WaitlistEntry).where(WaitlistEntry.created_at < cutoff))


# --------- eventos por ciudad (caché + presupuesto) ---------


async def mark_scanned(
    session: AsyncSession, city_key: str, found: int, source: str = "daily"
) -> None:
    row = await session.get(CityScan, city_key)
    if row is None:
        session.add(CityScan(city=city_key, scanned_at=_now(), source=source, events_found=found))
    else:
        row.scanned_at, row.source, row.events_found = _now(), source, found
    await session.flush()


def _aware(dt: datetime) -> datetime:
    from datetime import UTC

    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def _fresh(session: AsyncSession, city_key: str) -> bool:
    row = await session.get(CityScan, city_key)
    return row is not None and _aware(row.scanned_at) > _now() - timedelta(days=CACHE_DAYS)


async def searches_today(session: AsyncSession) -> int:
    row = await session.get(PublicMetric, (local_today(), CITY_SEARCH))
    return row.value if row else 0


async def _search_city(session: AsyncSession, m: Municipality, search, llm) -> int:
    """Busca los eventos de un municipio (2 consultas) y los guarda como públicos."""
    from app.market.extractor import extract_events
    from app.services import event_service

    queries = [
        f"eventos conciertos ferias festivales {m.city} {m.department} próximos meses",
        f"agenda de eventos importantes {m.city} {m.department}",
    ]
    found = 0
    for q in queries:
        results = await search.search(q)
        for cand in await extract_events(llm, results, m.city):
            await event_service.upsert_event(
                session, name=cand.name, start_date=cand.start_date, kind=cand.kind,
                end_date=cand.end_date, relevance=cand.relevance, location=cand.location,
                city=m.city_key,
            )
            found += 1
    return found


async def ensure_events(
    session: AsyncSession, m: Municipality, *, search, llm, budget: int
) -> str:
    """'cached' | 'searched' | 'budget_exhausted' | 'unavailable' (sin búsqueda configurada)."""
    if await _fresh(session, m.city_key):
        return "cached"
    if search is None or llm is None:
        return "unavailable"
    if await searches_today(session) >= budget:
        return "budget_exhausted"
    await bump(session, CITY_SEARCH)  # se cuenta antes: un fallo no permite gastar de más
    try:
        found = await _search_city(session, m, search, llm)
    except Exception as exc:  # noqa: BLE001 — el informe sigue con lo que haya guardado
        log.warning("busqueda publica fallida city=%s err=%s", m.city_key, type(exc).__name__)
        return "unavailable"
    await mark_scanned(session, m.city_key, found, source="public")
    return "searched"


# --------- informe ---------


@dataclass
class ReportInput:
    municipality_code: str
    weekday_price: Decimal
    weekend_price: Decimal | None = None
    currency: str = "COP"
    unit_kind: str | None = None
    language: str = "es"


def _validate(inp: ReportInput) -> Municipality:
    m = municipalities.get(inp.municipality_code)
    if m is None:
        raise PublicError("unknown_municipality", "Elige un municipio de la lista.", 404)
    for p in (inp.weekday_price, inp.weekend_price):
        if p is not None and not (Decimal("1") <= p <= MAX_PRICE):
            raise PublicError("invalid_data", "Revisa el precio por noche.", 400)
    return m


def _name_key(name: str) -> str:
    """'Beéle — Borondo Tour' y 'Beéle - Borondo Tour' son el mismo evento."""
    import re
    import unicodedata

    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


async def _events(session: AsyncSession, keys: list[str], today: date) -> list[Event]:
    until = today + timedelta(days=HORIZON_DAYS)
    rows = (
        await session.execute(
            select(Event).where(
                Event.city.in_(keys),
                Event.start_date <= until,
                or_(Event.end_date >= today, Event.start_date >= today),
            )
        )
    ).scalars().all()
    # Mismo evento visto en dos ciudades del área (p. ej. Medellín y Sabaneta): una vez.
    seen, out = set(), []
    for ev in sorted(rows, key=lambda e: (_REL_ORDER.get(e.relevance, 3), e.start_date)):
        k = (_name_key(ev.name), ev.start_date)
        if k not in seen:
            seen.add(k)
            out.append(ev)
    return out


def price_for(ev: Event, weekday: Decimal, weekend: Decimal | None, today: date) -> dict:
    night = max(ev.start_date, today)
    base = weekend if (weekend and night.weekday() in WEEKEND) else weekday
    out = suggest_price_v2(base, event=EventSignal(relevance=ev.relevance, name=ev.name))
    suggested = out.price if out else base
    pct = int(((suggested / base) - 1) * 100) if base else 0
    return {
        "name": ev.name,
        "start_date": ev.start_date.isoformat(),
        "end_date": (ev.end_date or ev.start_date).isoformat(),
        "relevance": ev.relevance.value,
        "kind": ev.kind.value,
        "location": ev.location,
        "base_price": str(base),
        "suggested_price": str(suggested),
        "pct": pct,
    }


def city_keys(m: Municipality) -> list[str]:
    core = municipalities.metro_core(m.code)
    return [m.city_key] + ([core.city_key] if core else [])


async def build_events(
    session: AsyncSession, m: Municipality, weekday: Decimal, weekend: Decimal | None,
    today: date | None = None,
) -> list[dict]:
    today = today or local_today()
    return [price_for(ev, weekday, weekend, today)
            for ev in await _events(session, city_keys(m), today)]


async def create_report(
    session: AsyncSession, inp: ReportInput, *, ip: str | None, search=None, llm=None,
) -> dict:
    from app.services import invite_service

    m = _validate(inp)
    await _take(session, visitor_id(ip), "report", REPORTS_PER_VISITOR_DAY)
    state = await invite_service.registration_state(session)
    statuses = []
    for target in [m] + ([c] if (c := municipalities.metro_core(m.code)) else []):
        statuses.append(
            await ensure_events(session, target, search=search, llm=llm,
                                budget=state["city_budget"])
        )
    events = await build_events(session, m, inp.weekday_price, inp.weekend_price)
    token = secrets.token_urlsafe(24)
    session.add(PublicReport(
        token_hash=digest(token), municipality_code=m.code, city=m.city_key,
        weekday_price=inp.weekday_price, weekend_price=inp.weekend_price,
        currency=(inp.currency or "COP")[:3].upper(),
        unit_kind=(inp.unit_kind or "")[:20] or None,
        language=inp.language if inp.language in LANGS else "es",
    ))
    await bump(session, REPORT)
    if all(s == "cached" for s in statuses):
        await bump(session, REPORT_CACHED)
    if events:
        status = "ok"
    elif statuses[0] == "budget_exhausted":
        status = "budget_exhausted"
    else:
        status = "no_events"
    await session.commit()
    return {
        "token": token,
        "municipality": m.as_dict(),
        "horizon_days": HORIZON_DAYS,
        "status": status,
        "events": events[:FREE_EVENTS],
        "total_events": len(events),
        "registration": {"open": state["open"], "full": state["full"]},
    }


async def find_report(session: AsyncSession, token: str | None) -> PublicReport | None:
    if not token:
        return None
    return (
        await session.execute(
            select(PublicReport).where(PublicReport.token_hash == digest(token.strip()))
        )
    ).scalar_one_or_none()


async def link_report(session: AsyncSession, token: str | None, account_id: int) -> bool:
    """Vincula un informe (aún sin cuenta) a la cuenta recién creada."""
    rep = await find_report(session, token)
    if rep is None or rep.account_id is not None:
        return False
    rep.account_id = account_id
    await bump(session, SIGNUP_FROM_REPORT)
    await session.flush()
    return True


async def report_of(session: AsyncSession, account_id: int) -> PublicReport | None:
    return (
        await session.execute(
            select(PublicReport)
            .where(PublicReport.account_id == account_id)
            .order_by(PublicReport.id.desc())
        )
    ).scalars().first()


async def full_report(session: AsyncSession, account_id: int) -> dict | None:
    rep = await report_of(session, account_id)
    m = municipalities.get(rep.municipality_code) if rep else None
    if rep is None or m is None:
        return None
    events = await build_events(session, m, rep.weekday_price, rep.weekend_price)
    return {
        "municipality": m.as_dict(),
        "city": m.city,
        "weekday_price": str(rep.weekday_price),
        "weekend_price": str(rep.weekend_price) if rep.weekend_price else None,
        "currency": rep.currency,
        "unit_kind": rep.unit_kind,
        "horizon_days": HORIZON_DAYS,
        "events": events,
        "generated_at": rep.created_at.isoformat() if rep.created_at else None,
    }


async def email_report_once(session: AsyncSession, account_id: int, email: str, lang: str,
                            sender) -> bool:
    """Envía el resumen del informe por correo una sola vez (tras verificar el correo).

    Solo los más importantes: la lista completa y actualizada vive en la app (retención)."""
    from app.email import templates

    rep = await report_of(session, account_id)
    if rep is None or rep.emailed_at is not None or sender is None:
        return False
    data = await full_report(session, account_id)
    if data is None:
        return False
    rep.emailed_at = _now()
    await session.flush()
    link = f"{settings.public_base_url.rstrip('/')}/report"
    await sender.send(templates.full_report(email, lang, data, link))
    return True


# --------- lista de espera ---------


async def join_waitlist(
    session: AsyncSession, *, email: str, consent: bool, language: str = "es",
    municipality_code: str | None = None, ip: str | None = None,
) -> None:
    from app.auth.tokens import normalize_email

    if not consent:
        raise PublicError("consent_required", "Necesitamos tu autorización para escribirte.", 400)
    email = normalize_email(email)
    if "@" not in email or len(email) > 254:
        raise PublicError("invalid_data", "Revisa el correo.", 400)
    await _take(session, visitor_id(ip), "waitlist", WAITLIST_PER_VISITOR_DAY)
    exists = (
        await session.execute(select(WaitlistEntry.id).where(WaitlistEntry.email == email))
    ).first()
    if exists is None:  # misma respuesta exista o no (no revela quién está en la lista)
        session.add(WaitlistEntry(
            email=email, language=language if language in LANGS else "es",
            municipality_code=municipality_code if municipalities.get(municipality_code or "")
            else None,
        ))
        await bump(session, WAITLIST)
    await session.commit()


# --------- administrador de plataforma ---------


async def metrics(session: AsyncSession, days: int = 30) -> list[dict]:
    since = local_today() - timedelta(days=days - 1)
    rows = (
        await session.execute(
            select(PublicMetric).where(PublicMetric.day >= since).order_by(PublicMetric.day)
        )
    ).scalars().all()
    return [{"day": r.day.isoformat(), "key": r.key, "value": r.value} for r in rows]


async def waitlist(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(select(WaitlistEntry).order_by(WaitlistEntry.id))
    ).scalars().all()
    out = []
    for w in rows:
        m = municipalities.get(w.municipality_code or "")
        out.append({
            "id": w.id, "email": w.email, "language": w.language,
            "municipality": m.label if m else None,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        })
    return out


async def reports_count(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(PublicReport))).scalar_one()
