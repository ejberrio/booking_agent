"""Las ÚNICAS operaciones entre cuentas fuera del panel de administrador (feature 026).

Van por la tabla (Core, sin entidad del ORM), así que el filtro por cuenta no aplica:
por eso viven aquí, son mínimas y devuelven solo lo imprescindible. Una prueba
(test_tenancy) falla si otro módulo consulta tablas de cuentas por `__table__`.
"""

from __future__ import annotations

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tenancy import ACCOUNT_KEY


class PropertyOwnedElsewhere(ValueError):
    """La propiedad del channel manager ya pertenece a otra cuenta (FR-022)."""


async def property_taken_elsewhere(
    session: AsyncSession, provider: str, external_ref: str
) -> bool:
    """¿Otra cuenta ya tiene esta propiedad del channel manager? Solo sí/no."""
    from app.models.property import Property

    t = Property.__table__
    row = (
        await session.execute(
            select(t.c.account_id).where(
                and_(t.c.provider == provider, t.c.external_ref == external_ref)
            )
        )
    ).first()
    return row is not None and row[0] != session.info.get(ACCOUNT_KEY)


async def release_push_token(session: AsyncSession, token: str) -> None:
    """Un teléfono recibe avisos solo de la cuenta con la que inició sesión: al registrarlo
    en la cuenta actual se quita de las demás."""
    from app.models.push import PushDevice

    t = PushDevice.__table__
    await session.execute(
        delete(t).where(and_(t.c.token == token, t.c.account_id != session.info[ACCOUNT_KEY]))
    )
