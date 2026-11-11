"""Feature 046 (#167): registro de huéspedes — validación, cifrado, enlace público y envío de la TRA."""

from __future__ import annotations

import json
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.api.routes import public
from app.models.booking import Booking
from app.models.enums import BookingStatus, ChannelKind
from app.models.property import Property, UnitType
from app.models.registration import TRA_ERROR, TRA_PARTIAL, TRA_SENT, GuestRegistration
from app.registration.tra import TraError
from app.services import privacy_service
from app.services import registration_service as svc

pytestmark = pytest.mark.anyio
TODAY = date.today()

FORM = {
    "main": {"doc_type": "PA", "doc_number": "X1234567", "first_names": "Carolina", "last_names": "Pérez Ruiz",
             "nationality": "MX", "birth_date": "1990-05-04"},
    "companions": [
        {"doc_type": "CC", "doc_number": "1.037.654.321", "first_names": "Juan", "last_names": "Gómez",
         "nationality": "CO"},
        {"doc_type": "RC", "doc_number": "1122334455", "first_names": "Ana", "last_names": "Gómez Pérez",
         "nationality": "CO"},
    ],
    "motive": "leisure", "residence_city": "Ciudad de México", "origin_city": "Bogotá",
    "destination_city": "Cartagena",
}


async def _booking(session, *, amount="1200000", currency="COP", days=3):
    prop = Property(name="Apto", city="Sabaneta", external_ref="p1")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="3BR Mayorca", external_ref="u1")
    session.add(unit)
    await session.flush()
    b = Booking(unit_type_id=unit.id, channel_kind=ChannelKind.booking, check_in=TODAY + timedelta(days=days),
                check_out=TODAY + timedelta(days=days + 3), status=BookingStatus.confirmed, external_ref="B1",
                guest_name="Carolina Pérez", amount=amount, currency=currency)
    session.add(b)
    await session.flush()
    return b


class FakeTra:
    def __init__(self, fail_companion: int | None = None, fail_main: bool = False):
        self.calls: list[tuple[str, dict]] = []
        self.fail_companion, self.fail_main = fail_companion, fail_main
        self.n = 0

    async def send_main(self, payload):
        self.calls.append(("one", payload))
        if self.fail_main:
            raise TraError("El MinCIT rechazó los datos (400).")
        return 19

    async def send_companion(self, payload):
        self.calls.append(("two", payload))
        self.n += 1
        if self.fail_companion is not None and self.n - 1 == self.fail_companion:
            raise TraError("El MinCIT respondió con un error (500).")
        return 100 + self.n

    async def aclose(self):
        return None


async def _configured(session):
    s = await svc.get_settings(session)
    s.rnt, s.establishment_name = "123456", "Apto Mayorca"
    s.authorized_at = s.created_at
    await session.flush()


def test_validacion():
    v = svc.validate(FORM, TODAY)
    assert v.errors == {}
    assert v.data["foreign"] is True
    assert v.data["companions"][0]["doc_number"] == "1037654321"  # sin puntos
    bad = json.loads(json.dumps(FORM))
    bad["main"]["doc_type"] = "RC"  # registro civil solo para acompañantes
    bad["main"]["birth_date"] = None  # extranjero sin nacimiento
    bad["companions"][0]["doc_number"] = "ABC123"  # cédula con letras
    bad["destination_city"] = ""
    e = svc.validate(bad, TODAY).errors
    assert {"doc_type", "birth_date"} <= set(e["main"])
    assert e["c0"] == ["doc_number"]
    assert "destination_city" in e["trip"]


async def test_datos_cifrados_por_cuenta(session):
    b = await _booking(session)
    reg = await svc.ensure(session, b.id)
    await svc.save(session, reg, FORM, by="guest", today=TODAY)
    assert "X1234567" not in reg.data_encrypted and "Carolina" not in reg.data_encrypted
    assert svc.data_of(reg)["main"]["doc_number"] == "X1234567"
    assert svc.decrypt(2, reg.data_encrypted) is None  # la clave de otra cuenta no sirve
    assert len(reg.token) >= 40


async def test_envio_tra_y_reintento(session):
    b = await _booking(session)
    await _configured(session)
    reg = await svc.ensure(session, b.id)
    await svc.save(session, reg, FORM, by="guest", today=TODAY)
    client = FakeTra(fail_companion=1)
    reg = await svc.send_tra(session, b.id, client)
    assert reg.status == TRA_PARTIAL and reg.tra_code == 19
    kind, main = client.calls[0]
    assert kind == "one"
    assert main["tipo_identificacion"] == "Pasaporte" and main["numero_identificacion"] == "X1234567"
    assert main["cuidad_residencia"] == "Ciudad de México" and main["motivo"] == "Vacaciones, recreo y ocio"
    assert main["numero_acompanantes"] == "2" and main["costo"] == "1200000"
    assert main["tipo_acomodacion"] == "Apartamento" and main["rnt_establecimiento"] == "123456"
    assert client.calls[1][1]["padre"] == 19 and client.calls[2][1]["tipo_identificacion"] == "R.C"
    # Reintento: no reenvía al principal ni al acompañante que ya quedó.
    retry = FakeTra()
    reg = await svc.send_tra(session, b.id, retry)
    assert reg.status == TRA_SENT and [k for k, _ in retry.calls] == ["two"]
    assert retry.calls[0][1]["nombres"] == "Ana"
    # Tras enviar, los datos quedan bloqueados.
    with pytest.raises(svc.RegistrationError):
        await svc.save(session, reg, FORM, by="guest", today=TODAY)


async def test_error_del_principal(session):
    b = await _booking(session)
    await _configured(session)
    reg = await svc.ensure(session, b.id)
    await svc.save(session, reg, FORM, by="host", today=TODAY)
    reg = await svc.send_tra(session, b.id, FakeTra(fail_main=True))
    assert reg.status == TRA_ERROR and reg.tra_code is None
    assert "Carolina" not in reg.tra_error and "X1234567" not in reg.tra_error


async def test_costo_en_usd_se_convierte(session, monkeypatch):
    from decimal import Decimal

    from app.services import fx_service

    async def rate(*a, **k):
        return Decimal("4000")

    monkeypatch.setattr(fx_service, "rate_for", rate)
    b = await _booking(session, amount="300", currency="USD")
    assert await svc.proposed_cost(session, b) == Decimal("1200000")


def _req():
    return SimpleNamespace(headers={"x-client-ip": "1.2.3.4"}, client=None)


async def test_enlace_publico(session):
    b = await _booking(session)
    reg = await svc.ensure(session, b.id)
    await session.commit()
    maker = session.info["maker"]
    async with maker() as anon:  # sin cuenta: como llega la página pública
        info = await public.checkin_info(reg.token, anon)
        assert info["unit"] == "3BR Mayorca" and "guest_name" not in info and info["submitted"] is False
    async with maker() as anon:
        r = await public.checkin_submit(reg.token, public.CheckinRequest(data=FORM, consent=False), _req(), anon)
        assert r.status_code == 422  # sin consentimiento
    async with maker() as anon:
        assert await public.checkin_submit(reg.token, public.CheckinRequest(data=FORM, consent=True), _req(), anon) == {"ok": True}
    async with maker() as anon:
        r = await public.checkin_info("x" * 43, anon)
        assert r.status_code == 404
    got = (await session.execute(select(GuestRegistration))).scalar_one()
    await session.refresh(got)
    assert got.filled_by == "guest" and got.consent_at is not None


async def test_enlace_vence_tras_la_salida(session):
    b = await _booking(session, days=-10)  # salió hace 7 días
    reg = await svc.ensure(session, b.id)
    await session.commit()
    async with session.info["maker"]() as anon:
        r = await public.checkin_info(reg.token, anon)
    assert r.status_code == 404


async def test_otra_cuenta_no_ve_el_registro(session, other_session):
    b = await _booking(session)
    await svc.ensure(session, b.id)
    await session.commit()
    with pytest.raises(LookupError):
        await svc.detail(other_session, b.id, TODAY)
    assert (await svc.overview(other_session, TODAY)) == []


async def test_retencion_un_anio(session):
    b = await _booking(session, days=-400)
    reg = await svc.ensure(session, b.id)
    await svc.save(session, reg, FORM, by="host", today=TODAY - timedelta(days=400))
    await session.commit()
    await privacy_service.purge_guest_names(session, 1, TODAY)
    await session.refresh(reg)
    assert reg.data_encrypted is None and reg.purged is True


async def test_exportacion_legible(session):
    from app.models.account import Account
    from app.models.auth import AppUser

    b = await _booking(session)
    reg = await svc.ensure(session, b.id)
    await svc.save(session, reg, FORM, by="guest", today=TODAY)
    user = AppUser(name="Ever", email="e@x.co")
    out = await privacy_service.export_account(session, user, Account(id=1, name="Mi cuenta"))
    row = out["tables"]["guest_registration"][0]
    assert "data_encrypted" not in row and row["data"]["main"]["doc_number"] == "X1234567"
