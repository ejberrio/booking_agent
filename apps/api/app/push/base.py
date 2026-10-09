"""Puerto provider-agnostic para avisos push (Principio II). FCM es un adaptador."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

PushStatus = Literal["ok", "invalid_token", "error"]


@dataclass(frozen=True)
class PushMessage:
    token: str
    title: str
    body: str
    data: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PushResult:
    status: PushStatus
    detail: str | None = None


class PushSender(Protocol):
    async def send(self, message: PushMessage) -> PushResult: ...

    async def aclose(self) -> None: ...
