from datetime import date
from decimal import Decimal

from app.models.agent import Conversation, LLMConfig, Message
from app.models.enums import MessageRole
from app.models.property import Property, UnitType
from app.services import pricing_service

DAY = date(2026, 7, 15)


async def make_unit(session) -> tuple[Property, UnitType]:
    prop = Property(name="Casa Medellín")
    session.add(prop)
    await session.flush()
    unit = UnitType(property_id=prop.id, name="Apartaestudio", units_count=1)
    session.add(unit)
    await session.flush()
    return prop, unit


async def test_message_links_price_change(session):
    _, unit = await make_unit(session)
    conv = Conversation(title="Ajuste de julio")
    session.add(conv)
    await session.flush()
    msg = Message(conversation_id=conv.id, role=MessageRole.user, content="sube el 15 de julio")
    session.add(msg)
    await session.flush()

    log = await pricing_service.set_base_price(
        session,
        unit_type_id=unit.id,
        day=DAY,
        new_price=Decimal("90000"),
        message_id=msg.id,
    )
    assert log.message_id == msg.id


async def test_llm_config_defaults(session):
    cfg = LLMConfig(params={"temperature": 0.2})
    session.add(cfg)
    await session.flush()
    assert cfg.provider == "openai"
    assert cfg.model_general == "gpt-4o-mini"
    assert cfg.model_actions == "gpt-4o"
    assert cfg.params == {"temperature": 0.2}
