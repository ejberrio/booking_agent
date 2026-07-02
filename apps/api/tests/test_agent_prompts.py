"""Feature 012: prompt del agente multi-canal (T014)."""

from __future__ import annotations

from datetime import date

from app.agent.prompts import system_prompt

DAY = date(2026, 7, 15)


def test_prompt_mentions_active_channels():
    p = system_prompt(DAY, active_channels=["booking", "airbnb"])
    assert "Booking.com y Airbnb" in p
    assert "solo el canal Booking" not in p


def test_prompt_declares_multichannel_publication_rule():
    p = system_prompt(DAY, active_channels=["booking", "airbnb"])
    # FR-006: cualquier cambio de precio/disponibilidad/promoción publica a TODOS
    # los canales conectados.
    assert "TODOS los canales conectados" in p


def test_prompt_instructs_channel_in_booking_answers():
    p = system_prompt(DAY, active_channels=["booking", "airbnb"])
    assert "get_bookings" in p
    assert "canal" in p.lower()


def test_prompt_backwards_compatible_without_channels():
    # Retro-compatibilidad: sin argumento asume el canal booking.
    p = system_prompt(DAY)
    assert "Booking.com" in p
    assert "HOY es" in p


def test_prompt_single_channel_reads_naturally():
    p = system_prompt(DAY, active_channels=["airbnb"])
    assert "Airbnb" in p
    assert " y " not in p.split("\n")[0]  # un solo canal: sin conjunción en la presentación


def test_prompt_keeps_existing_rules():
    p = system_prompt(DAY, active_channels=["booking", "airbnb"])
    # Reglas previas intactas (human-in-the-loop, deals con badge, fechas).
    assert "propose_" in p
    assert "badge" in p
    assert "HOY es" in p
