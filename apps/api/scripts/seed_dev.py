"""Datos de ejemplo para desarrollo.

Crea una propiedad con un tipo de unidad y canal Booking, fija un precio y
una promoción, y deja una sugerencia propuesta. Requiere Postgres corriendo
(make db-up) y migraciones aplicadas (alembic upgrade head).

Uso:
    cd apps/api && uv run python -m scripts.seed_dev
"""

import asyncio
from datetime import date
from decimal import Decimal

from app.db.session import SessionLocal
from app.models.enums import ChannelKind, EventKind, PromotionType
from app.models.pricing import Promotion
from app.models.property import Channel, Property, UnitType
from app.services import event_service, pricing_service


async def seed() -> None:
    async with SessionLocal() as session:
        prop = Property(name="Apartamento El Poblado", city="Medellín", currency="COP")
        session.add(prop)
        await session.flush()

        session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True))
        unit = UnitType(property_id=prop.id, name="Apartaestudio", units_count=1)
        session.add(unit)
        await session.flush()

        # Precio base para una semana
        for d in range(15, 22):
            await pricing_service.set_base_price(
                session,
                unit_type_id=unit.id,
                day=date(2026, 7, d),
                new_price=Decimal("180000"),
            )

        session.add(
            Promotion(
                property_id=prop.id,
                name="Lanzamiento -15%",
                discount_type=PromotionType.percent,
                discount_value=Decimal("15"),
                start_date=date(2026, 7, 15),
                end_date=date(2026, 7, 21),
            )
        )

        await event_service.upsert_event(
            session,
            name="Feria de las Flores",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 10),
            kind=EventKind.festival,
            location="Medellín",
        )

        await session.commit()
        print(f"Seed listo. Propiedad #{prop.id}, unidad #{unit.id}.")


if __name__ == "__main__":
    asyncio.run(seed())
