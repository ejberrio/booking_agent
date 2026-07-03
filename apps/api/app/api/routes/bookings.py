"""Lectura de reservas para la web (feature 016). Solo lectura, cero escrituras al CM.

El nombre del huésped es dato personal: viaja únicamente API→web autenticada y
nunca se registra en logs (el middleware solo loguea method/path/status).
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.booking import Booking
from app.models.enums import BookingStatus

router = APIRouter()


@router.get("")
async def list_bookings(
    unit_type_id: int, date_from: date, date_to: date, session: AsyncSession = Depends(get_session)
):
    """Reservas confirmadas cuya estancia solapa el rango (noches [check_in, check_out))."""
    rows = (
        (
            await session.execute(
                select(Booking)
                .where(
                    Booking.unit_type_id == unit_type_id,
                    Booking.status == BookingStatus.confirmed,
                    Booking.check_in <= date_to,
                    Booking.check_out > date_from,
                )
                .order_by(Booking.check_in, Booking.id)
            )
        )
        .scalars()
        .all()
    )
    return {
        "bookings": [
            {
                "id": b.id,
                "guest_name": b.guest_name,
                "channel": b.channel_kind.value,
                "check_in": b.check_in.isoformat(),
                "check_out": b.check_out.isoformat(),
                "nights": (b.check_out - b.check_in).days,
                "status": b.status.value,
                "external_ref": b.external_ref,
            }
            for b in rows
        ]
    }
