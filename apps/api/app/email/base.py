"""Puerto de correo transaccional (feature 026). Principio II: el proveedor es un adaptador."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> bool: ...
