"""Adaptador del Channel Manager de la cuenta del contexto (feature 026).

El adaptador no sabe de cuentas (principio II): recibe la credencial y los ids. Aquí se
resuelven los de la cuenta de la sesión — nunca de otra.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.beds24 import Beds24Adapter
from app.channels.beds24_v2 import Beds24V2Adapter
from app.core.config import settings
from app.db.tenancy import TenantContextMissing, current_account_id
from app.models.account import FIRST_ACCOUNT_ID

REFRESH_TOKEN = "beds24_refresh_token"


def _account(session: AsyncSession) -> int:
    account_id = current_account_id(session)
    if account_id is None:
        raise TenantContextMissing("adaptador del canal sin cuenta en el contexto")
    return account_id


def has_credentials(session: AsyncSession) -> bool:
    """¿La cuenta de la sesión tiene credencial del Channel Manager?"""
    from app.services.secret_service import get_secret

    account_id = _account(session)
    if account_id == FIRST_ACCOUNT_ID and settings.beds24_api_version != "v2":
        return bool(settings.beds24_api_key)
    return bool(get_secret(REFRESH_TOKEN, account_id))


def get_adapter(session: AsyncSession):
    """Adaptador construido por petición: una rotación del token aplica de inmediato."""
    from app.services.secret_service import get_secret

    account_id = _account(session)
    first = account_id == FIRST_ACCOUNT_ID
    # La cuenta nº 1 conserva su configuración de entorno (V1 de solo lectura o V2).
    if first and settings.beds24_api_version != "v2":
        return Beds24Adapter(
            api_key=settings.beds24_api_key,
            prop_key=settings.beds24_prop_key,
            prop_id=settings.beds24_prop_id,
            room_id=settings.beds24_room_id,
            base_url=settings.beds24_base_url,
        )
    # Los roomId de Beds24 son únicos globalmente; propertyId solo es un valor por
    # defecto opcional para precios fijos (la cuenta nº 1 mantiene el suyo).
    return Beds24V2Adapter(
        refresh_token=get_secret(REFRESH_TOKEN, account_id),
        prop_id=settings.beds24_prop_id if first else None,
        room_id=settings.beds24_room_id if first else None,
        base_url=settings.beds24_v2_base_url,
    )
