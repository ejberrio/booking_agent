"""Panel del administrador de plataforma (feature 026, entrega 3). Solo `is_platform_admin`."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, require_platform_admin
from app.db.session import get_session
from app.services import admin_service, invite_service

router = APIRouter(dependencies=[Depends(require_platform_admin)])


@router.get("/invites")
async def list_invites(session: AsyncSession = Depends(get_session)):
    return await invite_service.list_invites(session)


class InviteCreate(BaseModel):
    note: str | None = Field(default=None, max_length=200)
    days: int = Field(default=30, ge=1, le=180)


@router.post("/invites")
async def create_invite(
    req: InviteCreate,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_platform_admin),
):
    inv, code = await invite_service.create(
        session, note=req.note, days=req.days, by_user_id=ctx.user_id
    )
    await session.commit()
    # ÚNICA vez que el código completo sale de la API.
    return {"id": inv.id, "code": code, "note": inv.note, "expires_at": inv.expires_at.isoformat()}


@router.delete("/invites/{invite_id}")
async def revoke_invite(invite_id: int, session: AsyncSession = Depends(get_session)):
    try:
        await invite_service.revoke(session, invite_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    await session.commit()
    return {"revoked": True}


@router.get("/accounts")
async def list_accounts():
    return await admin_service.list_accounts()


@router.post("/accounts/{account_id}/disable")
async def disable_account(account_id: int, ctx: RequestContext = Depends(require_platform_admin)):
    try:
        return await admin_service.set_status(account_id, enabled=False, by_account_id=ctx.account_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.post("/accounts/{account_id}/enable")
async def enable_account(account_id: int, ctx: RequestContext = Depends(require_platform_admin)):
    try:
        return await admin_service.set_status(account_id, enabled=True, by_account_id=ctx.account_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.get("/settings")
async def get_settings(session: AsyncSession = Depends(get_session)):
    state = await invite_service.registration_state(session)
    return {"registration_open": state["enabled"]}


class SettingsPatch(BaseModel):
    registration_open: bool


@router.patch("/settings")
async def patch_settings(req: SettingsPatch, session: AsyncSession = Depends(get_session)):
    await invite_service.set_registration_open(session, req.registration_open)
    await session.commit()
    return {"registration_open": req.registration_open}


# --------- beta pública (feature 030) ---------


@router.get("/beta")
async def beta(session: AsyncSession = Depends(get_session)):
    from app.services import public_service

    state = await invite_service.registration_state(session)
    return {
        "enabled": state["enabled"],
        "quota": state["quota"],
        "used": state["used"],
        "full": state["full"],
        "city_budget": state["city_budget"],
        "searches_today": await public_service.searches_today(session),
        "reports_total": await public_service.reports_count(session),
        "metrics": await public_service.metrics(session),
        "waitlist": await public_service.waitlist(session),
    }


class BetaPatch(BaseModel):
    enabled: bool | None = None
    quota: int | None = Field(default=None, ge=0, le=100000)
    city_budget: int | None = Field(default=None, ge=0, le=1000)


@router.patch("/beta")
async def patch_beta(req: BetaPatch, session: AsyncSession = Depends(get_session)):
    await invite_service.update_registration(
        session, enabled=req.enabled, quota=req.quota, city_budget=req.city_budget
    )
    await session.commit()
    return await beta(session)


@router.post("/waitlist/{entry_id}/invite")
async def invite_from_waitlist(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_platform_admin),
):
    from app.core.config import settings
    from app.email import templates
    from app.models.public import WaitlistEntry
    from app.services.auth_service import get_email_sender

    entry = await session.get(WaitlistEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No existe esa entrada")
    sender = get_email_sender()
    if sender is None:
        raise HTTPException(status_code=503, detail="El correo no está disponible")
    inv, code = await invite_service.create(
        session, note="Lista de espera", days=invite_service.DEFAULT_DAYS, by_user_id=ctx.user_id
    )
    link = f"{settings.public_base_url.rstrip('/')}/register?code={code}"
    email, lang = entry.email, entry.language
    await session.delete(entry)  # el correo solo se guardaba para esto (Ley 1581)
    await session.commit()
    await sender.send(templates.waitlist_invite(email, lang, link, invite_service.DEFAULT_DAYS))
    return {"invited": True, "invite_id": inv.id}


@router.delete("/waitlist/{entry_id}")
async def delete_waitlist(entry_id: int, session: AsyncSession = Depends(get_session)):
    from app.models.public import WaitlistEntry

    entry = await session.get(WaitlistEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No existe esa entrada")
    await session.delete(entry)
    await session.commit()
    return {"deleted": True}


# --------- mercado (feature 038) ---------


class MarketBandsIn(BaseModel):
    city: str = Field(min_length=2, max_length=80)
    bedrooms: int = Field(default=0, ge=0, le=20)
    source: str = Field(default="pricelabs", max_length=40)
    rows: list[list | dict] = Field(min_length=1, max_length=800)


@router.post("/market-bands")
async def import_market_bands(req: MarketBandsIn, session: AsyncSession = Depends(get_session)):
    """Importa percentiles de precio por fecha (p. ej. PriceLabs → Precios Futuros)."""
    from app.services import market_band_service

    try:
        n = await market_band_service.import_rows(
            session, city=req.city, bedrooms=req.bedrooms, rows=req.rows, source=req.source
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Filas inválidas: {exc}") from None
    await session.commit()
    return {"imported": n, "bands": await market_band_service.summary(session)}


@router.get("/market-bands")
async def market_bands(session: AsyncSession = Depends(get_session)):
    from app.services import market_band_service

    return await market_band_service.summary(session)


class MarketCsvIn(BaseModel):
    city: str = Field(min_length=2, max_length=80)
    bedrooms: int = Field(default=0, ge=0, le=20)
    csv: str = Field(min_length=10, max_length=400_000)  # ~3 años de fechas ≈ 80 KB


@router.post("/market-bands/csv")
async def import_market_csv(req: MarketCsvIn, session: AsyncSession = Depends(get_session)):
    """Carga el CSV de PriceLabs → "Precios Futuros" para una zona y un número de habitaciones
    (feature 040). Reemplaza las fechas que ya existían; las demás se conservan."""
    from app.domain import municipalities
    from app.services import market_band_service

    key = municipalities.area_core_key(req.city)
    if municipalities.by_city_key(key) is None:
        raise HTTPException(status_code=400, detail=f"No reconozco el municipio \"{req.city}\".")
    try:
        parsed = market_band_service.parse_csv(req.csv)
    except market_band_service.CsvError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    n = await market_band_service.import_rows(
        session, city=req.city, bedrooms=req.bedrooms, rows=parsed.rows, source="pricelabs"
    )
    await session.commit()
    return {
        "imported": n, "past": parsed.past, "invalid": parsed.invalid, "city": key,
        "from": parsed.rows[0][0], "to": parsed.rows[-1][0],
        "bands": await market_band_service.summary(session),
    }


@router.delete("/market-bands")
async def delete_market_bands(city: str, bedrooms: int, session: AsyncSession = Depends(get_session)):
    from app.services import market_band_service

    n = await market_band_service.delete_zone(session, city=city, bedrooms=bedrooms)
    await session.commit()
    return {"deleted": n, "bands": await market_band_service.summary(session)}


# --------- mercado por la API de PriceLabs (feature 041) ---------


class MarketFeedIn(BaseModel):
    city: str = Field(min_length=2, max_length=80)
    bedrooms: int = Field(default=0, ge=0, le=20)
    listing_id: str = Field(min_length=1, max_length=80)
    pms: str = Field(min_length=1, max_length=40)
    enabled: bool = True


async def _with_client(fn):
    from app.market.pricelabs import PriceLabsClient, PriceLabsError

    try:
        client = PriceLabsClient()
    except PriceLabsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    try:
        return await fn(client)
    except PriceLabsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    finally:
        await client.aclose()


@router.get("/pricelabs/listings")
async def pricelabs_listings():
    """Anuncios de la cuenta de PriceLabs (para elegir de cuál leer el vecindario)."""
    return await _with_client(lambda c: c.listings())


@router.get("/market-feeds")
async def market_feeds(session: AsyncSession = Depends(get_session)):
    from app.services import market_feed_service

    return await market_feed_service.list_feeds(session)


@router.post("/market-feeds")
async def save_market_feed(req: MarketFeedIn, session: AsyncSession = Depends(get_session)):
    """Guarda la configuración y la prueba de una vez (importa si PriceLabs responde)."""
    from app.services import market_feed_service

    try:
        feed = await market_feed_service.save_feed(
            session, city=req.city, bedrooms=req.bedrooms, listing_id=req.listing_id,
            pms=req.pms, enabled=req.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    result = await _run(session, feed)
    await session.commit()
    return {"result": result, "feeds": await market_feed_service.list_feeds(session)}


async def _run(session, feed):
    from app.market.pricelabs import PriceLabsClient, PriceLabsError
    from app.services import market_feed_service

    try:
        client = PriceLabsClient()
    except PriceLabsError as exc:
        return {"ok": False, "error": str(exc)}
    try:
        return await market_feed_service.run_feed(session, feed, client)
    finally:
        await client.aclose()


@router.post("/market-feeds/{feed_id}/run")
async def run_market_feed(feed_id: int, session: AsyncSession = Depends(get_session)):
    from app.models.market import MarketFeed
    from app.services import market_feed_service

    feed = await session.get(MarketFeed, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="No existe esa configuración")
    result = await _run(session, feed)
    await session.commit()
    return {"result": result, "feeds": await market_feed_service.list_feeds(session)}


@router.delete("/market-feeds/{feed_id}")
async def delete_market_feed(feed_id: int, session: AsyncSession = Depends(get_session)):
    from app.services import market_feed_service

    try:
        await market_feed_service.delete_feed(session, feed_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    await session.commit()
    return {"deleted": True, "feeds": await market_feed_service.list_feeds(session)}


# --------- uso de IA (feature 027) ---------


@router.get("/usage")
async def ai_usage(month: str | None = None):
    from datetime import date

    from app.services.usage_service import local_today

    try:
        day = date.fromisoformat(f"{month}-01") if month else local_today()
    except ValueError:
        raise HTTPException(status_code=422, detail="Mes inválido (AAAA-MM)") from None
    return await admin_service.usage(day)


class LimitsRequest(BaseModel):
    model_config = {"extra": "forbid"}

    chat_limit_month: int | None = Field(default=None, ge=0, le=100_000)
    search_limit_day: int | None = Field(default=None, ge=0, le=1_000)


@router.patch("/accounts/{account_id}/limits")
async def set_limits(account_id: int, req: LimitsRequest):
    fields = {k: getattr(req, k) for k in req.model_fields_set}
    try:
        return await admin_service.set_limits(account_id, **fields)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
