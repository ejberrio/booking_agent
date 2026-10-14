"""Feature 030: página pública, informe gratis, registro abierto con cupo y lista de espera."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.api.routes import public as public_routes
from app.db.session import get_session
from app.db.tenancy import mark_platform
from app.domain import municipalities
from app.email.fake import FakeEmailSender
from app.main import app
from app.models.account import Account
from app.models.enums import EventKind, Relevance
from app.models.public import PublicReport, WaitlistEntry
from app.services import admin_service, auth_service, event_service, public_service
from app.services.usage_service import local_today

pytestmark = pytest.mark.anyio

PWD = "una-clave-larga-1"
SABANETA, MEDELLIN, GUATAPE, JARDIN = "05631", "05001", "05321", "05364"


def test_municipios_lista_oficial_y_claves():
    assert municipalities.count() == 1122
    labels = [m.label for m in municipalities.search("sabane")]
    assert "Sabaneta, Antioquia" in labels
    cali = municipalities.search("cali")[0]
    assert cali.city == "Cali" and cali.city_key == "cali"
    assert municipalities.metro_core(SABANETA).code == MEDELLIN
    assert municipalities.metro_core(GUATAPE) is None
    # nombres repetidos: el de Antioquia conserva la clave simple, el otro lleva departamento
    rio = {m.department: m.city_key for m in municipalities.search("rionegro")}
    assert rio["Antioquia"] == "rionegro" and rio["Santander"] == "rionegro santander"
    assert municipalities.search("x") == []


def test_visitante_no_guarda_la_ip_y_cambia_cada_dia():
    today = local_today()
    a = public_service.visitor_id("181.50.1.2", today)
    assert "181" not in a and len(a) == 32
    assert a != public_service.visitor_id("181.50.1.2", today + timedelta(days=1))


@pytest.fixture
def mail(monkeypatch):
    sender = FakeEmailSender()
    monkeypatch.setattr(auth_service, "get_email_sender", lambda: sender)
    return sender


@pytest.fixture
def searches(monkeypatch):
    """Búsqueda pública falsa: registra las ciudades buscadas y guarda un evento."""
    calls: list[str] = []

    async def fake_search_city(session, m, search, llm):
        calls.append(m.city_key)
        await event_service.upsert_event(
            session, name=f"Fiesta de {m.city}", start_date=local_today() + timedelta(days=30),
            kind=EventKind.festival, relevance=Relevance.medium, city=m.city_key,
        )
        return 1

    monkeypatch.setattr(public_service, "_search_city", fake_search_city)
    monkeypatch.setattr(public_routes, "search_provider", lambda: object())
    monkeypatch.setattr(public_routes, "llm_provider", lambda: object())
    return calls


@pytest_asyncio.fixture
async def client(session, monkeypatch):
    maker = session.info["maker"]

    async def _fresh():
        async with maker() as s:
            yield s

    @asynccontextmanager
    async def fake_platform():
        async with maker() as s:
            mark_platform(s)
            yield s

    monkeypatch.setattr(admin_service, "platform_session", fake_platform)
    app.dependency_overrides[get_session] = _fresh
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _admin(client) -> str:
    r = await client.post("/auth/claim", json={"name": "Host", "email": "host@example.com",
                                               "password": PWD, "accept_terms": True})
    return r.json()["token"]


async def _report(client, code=SABANETA, ip="1.1.1.1", **kw):
    body = {"municipality_code": code, "weekday_price": 250000, **kw}
    return await client.post("/public/report", json=body, headers={"x-client-ip": ip})


async def _seed_medellin(session):
    today = local_today()
    friday = today + timedelta(days=(4 - today.weekday()) % 7 + 7)
    for i, (rel, start) in enumerate([
        (Relevance.high, friday), (Relevance.medium, today + timedelta(days=20)),
        (Relevance.low, today + timedelta(days=40)), (Relevance.high, today + timedelta(days=60)),
        (Relevance.high, today + timedelta(days=400)),  # fuera de los 6 meses
    ]):
        await event_service.upsert_event(session, name=f"Evento {i}", start_date=start,
                                         kind=EventKind.concert, relevance=rel, city="Medellín")
    await public_service.mark_scanned(session, "medellin", 5)
    await public_service.mark_scanned(session, "sabaneta", 0)
    await session.commit()
    return friday


async def test_informe_desde_cache_top3_y_precio_de_fin_de_semana(client, session, searches):
    friday = await _seed_medellin(session)
    r = await _report(client, weekend_price=300000)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "ok" and data["total_events"] == 4 and len(data["events"]) == 3
    assert searches == []  # Sabaneta y Medellín estaban en caché: sin costo
    top = data["events"][0]
    assert top["relevance"] == "high" and top["start_date"] == friday.isoformat()
    assert top["base_price"] == "300000" and top["suggested_price"] == "390000" and top["pct"] == 30
    assert [e["relevance"] for e in data["events"]] == ["high", "high", "medium"]
    assert data["municipality"]["label"] == "Sabaneta, Antioquia"


async def test_ciudad_nueva_se_busca_una_vez_y_respeta_el_presupuesto(client, session, searches):
    admin = await _admin(client)
    await client.patch("/admin/beta", headers=_auth(admin), json={"city_budget": 1})
    r = await _report(client, GUATAPE)
    assert r.json()["status"] == "ok" and searches == ["guatape"]
    await _report(client, GUATAPE, ip="2.2.2.2")
    assert searches == ["guatape"]  # segunda vez: caché
    r = await _report(client, JARDIN)
    assert r.json()["status"] == "budget_exhausted" and searches == ["guatape"]
    beta = (await client.get("/admin/beta", headers=_auth(admin))).json()
    assert beta["searches_today"] == 1 and beta["reports_total"] == 3


async def test_limite_por_visitante_y_validaciones(client, session, searches, monkeypatch):
    monkeypatch.setattr(public_service, "REPORTS_PER_VISITOR_DAY", 2)
    await _seed_medellin(session)
    assert (await _report(client)).status_code == 200
    assert (await _report(client)).status_code == 200
    r = await _report(client)
    assert r.status_code == 429 and r.json()["code"] == "rate_limited"
    assert (await _report(client, ip="9.9.9.9")).status_code == 200
    assert (await _report(client, "99999", ip="8.8.8.8")).status_code == 404
    assert (await _report(client, ip="8.8.8.8", weekday_price=0)).status_code == 422


async def test_cupo_registro_desde_informe_correo_y_lista_de_espera(client, session, mail, searches):
    await _seed_medellin(session)
    admin = await _admin(client)
    await client.patch("/admin/beta", headers=_auth(admin), json={"enabled": True, "quota": 1})
    token = (await _report(client)).json()["token"]
    st = (await client.get("/auth/registration-status")).json()
    assert st == {"open": True, "full": False}

    r = await client.post("/auth/register", json={
        "name": "Ana", "email": "ana@example.com", "password": PWD, "accept_terms": True,
        "report": token})
    assert r.status_code == 202, r.text
    link = re.search(r"token=([A-Za-z0-9_\-]+)", mail.sent[-1].text).group(1)
    tok = (await client.post("/auth/verify-email", json={"token": link})).json()["token"]
    # informe completo por correo (una vez) y en la app
    assert "Sabaneta, Antioquia" in mail.sent[-1].subject and "325.000" in mail.sent[-1].text
    assert "Evento 0" in mail.sent[-1].text
    mine = (await client.get("/report/mine", headers=_auth(tok))).json()
    assert len(mine["events"]) == 4 and mine["city"] == "Sabaneta"
    assert mine["weekday_price"] == "250000.00"
    async with session.info["maker"]() as s:
        acc = (await s.execute(select(Account).where(Account.name == "Ana"))).scalar_one()
        assert acc.signup_source == "open"
        rep = (await s.execute(select(PublicReport))).scalars().first()
        assert rep.account_id == acc.id and rep.emailed_at is not None

    # cupo lleno: sin invitación → beta_full; la lista de espera pide consentimiento
    assert (await client.get("/auth/registration-status")).json() == {"open": False, "full": True}
    r = await client.post("/auth/register", json={
        "name": "Bea", "email": "bea@example.com", "password": PWD, "accept_terms": True})
    assert r.json()["code"] == "beta_full"
    w = {"email": "Bea@Example.com", "municipality_code": GUATAPE}
    assert (await client.post("/public/waitlist", json=w)).status_code == 400
    assert (await client.post("/public/waitlist", json={**w, "consent": True})).json() == {"ok": True}
    assert (await client.post("/public/waitlist", json={**w, "consent": True})).json() == {"ok": True}
    beta = (await client.get("/admin/beta", headers=_auth(admin))).json()
    assert beta["full"] and beta["used"] == 1 and len(beta["waitlist"]) == 1
    entry = beta["waitlist"][0]
    assert entry["email"] == "bea@example.com" and entry["municipality"] == "Guatapé, Antioquia"
    keys = {(m["key"]) for m in beta["metrics"]}
    assert {"report", "signup_open", "signup_from_report", "waitlist"} <= keys

    # invitar desde la lista: correo con el enlace y la entrada se borra
    r = await client.post(f"/admin/waitlist/{entry['id']}/invite", headers=_auth(admin))
    assert r.status_code == 200, r.text
    code = re.search(r"code=(SL-[0-9A-Z]{4}-[0-9A-Z]{4})", mail.sent[-1].text).group(1)
    async with session.info["maker"]() as s:
        assert (await s.execute(select(WaitlistEntry))).first() is None
    # la invitación funciona aunque el cupo esté lleno y no lo consume
    r = await client.post("/auth/register", json={
        "name": "Bea", "email": "bea@example.com", "password": PWD, "accept_terms": True,
        "invite_code": code})
    assert r.status_code == 202
    assert (await client.get("/admin/beta", headers=_auth(admin))).json()["used"] == 1


async def test_aislamiento_y_visitas(client, session, mail):
    admin = await _admin(client)
    # la cuenta del admin no viene de un informe
    assert (await client.get("/report/mine", headers=_auth(admin))).status_code == 404
    assert (await client.post("/public/visit")).json() == {"ok": True}
    beta = (await client.get("/admin/beta", headers=_auth(admin))).json()
    assert any(m["key"] == "visit" and m["value"] == 1 for m in beta["metrics"])
    # el panel beta es solo del administrador de plataforma
    await client.patch("/admin/beta", headers=_auth(admin), json={"enabled": True})
    await client.post("/auth/register", json={
        "name": "Ana", "email": "ana@example.com", "password": PWD, "accept_terms": True})
    link = re.search(r"token=([A-Za-z0-9_\-]+)", mail.sent[-1].text).group(1)
    tok = (await client.post("/auth/verify-email", json={"token": link})).json()["token"]
    assert (await client.get("/admin/beta", headers=_auth(tok))).status_code == 403
    assert (await client.get("/report/mine", headers=_auth(tok))).status_code == 404
