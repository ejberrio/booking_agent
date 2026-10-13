"""Adaptador de Resend (API HTTP). Nunca registra el destinatario ni el contenido."""

from __future__ import annotations

import logging

import httpx

from app.email.base import EmailMessage

log = logging.getLogger(__name__)

API_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "StayLever <no-reply@mail.staylever.com>"


class ResendSender:
    def __init__(self, api_key: str, *, sender: str = DEFAULT_FROM, client=None):
        self.api_key = api_key
        self.sender = sender
        self.client = client

    async def send(self, message: EmailMessage) -> bool:
        body = {
            "from": self.sender,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text,
            "html": message.html,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            if self.client is not None:
                r = await self.client.post(API_URL, json=body, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=15) as c:
                    r = await c.post(API_URL, json=body, headers=headers)
        except httpx.HTTPError as exc:
            log.warning("correo: Resend no respondió (%s)", type(exc).__name__)
            return False
        if r.status_code >= 300:
            log.warning("correo: Resend rechazó el envío (HTTP %s)", r.status_code)
            return False
        return True
