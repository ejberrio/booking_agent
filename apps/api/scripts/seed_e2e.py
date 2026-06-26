"""Siembra de datos para la prueba E2E (usa el propId/roomId reales de Beds24).

Crea propiedad/unidad/canal, regla de precios, precios para ~60 días, un evento
y la config de LLM. Uso: cd apps/api && uv run python -m scripts.seed_e2e
"""

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.agent import LLMConfig
from app.models.calendar import CalendarDay
from app.models.enums import ChannelKind, EventKind, Relevance
from app.models.market import Event
from app.models.pricing import PricingRule
from app.models.property import Channel, Property, UnitType
from app.services import pricing_service


async def main() -> None:
    async with SessionLocal() as session:
        existing = (await session.execute(select(Property))).scalars().first()
        if existing:
            print("Ya hay datos; nada que sembrar.")
            return

        prop = Property(name="Apartamento con piscina", city="Medellín", currency="COP",
                        external_ref="337229")
        session.add(prop)
        await session.flush()
        session.add(Channel(property_id=prop.id, kind=ChannelKind.booking, is_active=True,
                            external_ref="337229"))
        unit = UnitType(property_id=prop.id, name="Three-Bedroom Apartment", units_count=1,
                        external_ref="697411")
        session.add(unit)
        session.add(PricingRule(property_id=prop.id, min_price=Decimal("80000"),
                                max_price=Decimal("1200000")))
        await session.flush()

        today = date.today()
        for i in range(60):
            day = today + timedelta(days=i)
            await pricing_service.set_base_price(
                session, unit_type_id=unit.id, day=day, new_price=Decimal("180000")
            )
            # algo de ocupación (un fin de semana lleno)
            if day.weekday() in (4, 5) and i < 14:
                session.add(CalendarDay(unit_type_id=unit.id, date=day, units_available=0))

        session.add(
            Event(name="Feria de las Flores", start_date=date(2026, 8, 1), end_date=date(2026, 8, 10),
                  kind=EventKind.festival, relevance=Relevance.high, location="Medellín",
                  dedup_key="feria de las flores|2026-08-01|medellín")
        )
        session.add(LLMConfig(provider="openai", model_general="gpt-4o-mini",
                              model_actions="gpt-4o", is_active=True))
        await session.commit()
        print(f"Seed E2E listo: propiedad #{prop.id}, unidad #{unit.id} (60 días de precios).")
        print(f"Fecha de hoy: {datetime.now(UTC).date()}")


if __name__ == "__main__":
    asyncio.run(main())
