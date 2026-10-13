"""Feature 026: filtro automático por cuenta en el ORM (principio VI, falla cerrado)."""

from __future__ import annotations

import pathlib
import re

import pytest
from sqlalchemy import delete, func, select, update

from app.db.tenancy import CrossTenantWrite, TenantContextMissing, mark_platform, set_tenant
from app.models.property import Property, UnitType

pytestmark = pytest.mark.anyio

APP = pathlib.Path(__file__).resolve().parents[1] / "app"
SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"


async def _prop(session, name, ref):
    prop = Property(name=name, external_ref=ref)
    session.add(prop)
    await session.flush()
    session.add(UnitType(property_id=prop.id, name=f"{name}-u", external_ref=f"{ref}-r"))
    await session.commit()
    return prop


async def test_cada_cuenta_ve_y_modifica_solo_lo_suyo(session, other_session):
    a = await _prop(session, "A", "100")
    b = await _prop(other_session, "B", "200")
    assert a.account_id == 1 and b.account_id == 2  # before_flush rellena la cuenta

    assert [p.name for p in (await session.execute(select(Property))).scalars()] == ["A"]
    assert await session.get(Property, b.id) is None
    assert (await session.execute(select(func.count()).select_from(UnitType))).scalar() == 1
    # join + columnas sueltas
    rows = (await session.execute(select(UnitType.name).join(Property))).scalars().all()
    assert rows == ["A-u"]
    # UPDATE/DELETE del ORM no cruzan cuentas
    await session.execute(update(Property).values(name="X"))
    await session.execute(delete(UnitType).where(UnitType.property_id == b.id))
    await session.commit()
    name = (await other_session.execute(select(Property.name).where(Property.id == b.id))).scalar()
    assert name == "B"
    assert (await other_session.execute(select(func.count()).select_from(UnitType))).scalar() == 1


async def test_falla_cerrado_sin_cuenta(session):
    maker = session.info["maker"]
    async with maker() as bare:
        with pytest.raises(TenantContextMissing):
            await bare.execute(select(Property))
        with pytest.raises(TenantContextMissing):
            await bare.get(Property, 1)
        bare.add(Property(name="sin cuenta"))
        with pytest.raises(TenantContextMissing):
            await bare.flush()


async def test_no_se_escribe_en_otra_cuenta(session, other_session):
    session.add(Property(name="intruso", account_id=2))
    with pytest.raises(CrossTenantWrite):
        await session.flush()
    await session.rollback()
    with pytest.raises(CrossTenantWrite):
        set_tenant(session, 2)  # una sesión no cambia de cuenta
    with pytest.raises(CrossTenantWrite):
        mark_platform(session)


async def test_plataforma_ve_todas(session, other_session):
    await _prop(session, "A", "100")
    await _prop(other_session, "B", "200")
    async with session.info["maker"]() as plat:
        mark_platform(plat)
        names = sorted(p.name for p in (await plat.execute(select(Property))).scalars())
    assert names == ["A", "B"]


def _sources():
    for base in (APP, SCRIPTS):
        for path in base.rglob("*.py"):
            yield path, path.read_text()


def test_bypass_solo_en_modulos_permitidos():
    """Consultas entre cuentas: SOLO tenancy (definición), cross_account, el panel de
    administrador y el recorrido del cron."""
    allowed_platform = {"tenancy.py", "admin_service.py", "scan_daily.py"}
    allowed_table = {"cross_account.py"}
    for path, text in _sources():
        if re.search(r"\bplatform_session\(|\bmark_platform\(", text):
            assert path.name in allowed_platform, f"bypass de plataforma en {path}"
        if re.search(r"\b[A-Z]\w+\.__table__\b", text) and "models" not in path.parts:
            assert path.name in allowed_table, f"consulta por __table__ en {path}"
