"""Capa LLM provider-agnostic.

Envuelve LiteLLM para poder cambiar de modelo/proveedor desde configuración.
Expone un Protocol `LLM` inyectable: en producción `LiteLLMClient`; en tests un
FakeLLM con respuestas/tool-calls guionizados (sin gastar tokens).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import settings

SYSTEM_PROMPT = (
    "Eres el asistente de pricing de un host en Booking.com. "
    "Ayudas a consultar y ajustar precios por dia, rango y promociones. "
    "Nunca apliques cambios sin confirmacion explicita del host."
)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLM(Protocol):
    async def chat(
        self, *, messages: list[dict], tools: list[dict], model: str
    ) -> LLMResponse: ...


def _has_key() -> bool:
    return bool(settings.anthropic_api_key or settings.openai_api_key)


def _qualify(model: str) -> str:
    if settings.llm_provider and "/" not in model:
        return f"{settings.llm_provider}/{model}"
    return model


class LiteLLMClient:
    """Implementación real del puerto LLM sobre LiteLLM (tool-calling)."""

    async def chat(
        self, *, messages: list[dict], tools: list[dict], model: str
    ) -> LLMResponse:
        import litellm

        kwargs: dict[str, Any] = {"model": _qualify(model), "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = await litellm.acompletion(**kwargs)
        msg = resp.choices[0].message
        calls: list[ToolCall] = []
        for tc in getattr(msg, "tool_calls", None) or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except (json.JSONDecodeError, TypeError):
                args = {}
            calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        return LLMResponse(content=msg.content, tool_calls=calls)


def default_llm() -> LLM | None:
    """Devuelve el cliente LLM real si hay credenciales; si no, None (modo sin LLM)."""
    return LiteLLMClient() if _has_key() else None


async def complete(message: str) -> str:
    """Compatibilidad: respuesta simple sin herramientas (endpoint /chat placeholder)."""
    if not _has_key():
        return (
            "[modo demo: no hay API key de LLM configurada] "
            f"Recibi tu mensaje: '{message}'. "
            "Configura OPENAI_API_KEY (o ANTHROPIC_API_KEY) en .env para activar el agente."
        )
    import litellm

    response = await litellm.acompletion(
        model=_qualify(settings.llm_model),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )
    return response.choices[0].message.content or ""
