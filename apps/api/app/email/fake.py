"""Correo falso para pruebas: guarda los mensajes en memoria."""

from __future__ import annotations

from app.email.base import EmailMessage


class FakeEmailSender:
    def __init__(self):
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> bool:
        self.sent.append(message)
        return True
