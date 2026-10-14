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
    "Eres StayLever, el asistente de precios de un anfitrión de alquiler vacacional. "
    "Ayudas a consultar y ajustar precios, promociones y disponibilidad. "
    "Nunca apliques cambios sin confirmación explícita del anfitrión."
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
    # Feature 027: tokens consumidos (entrada, salida) y modelo, para medir el uso por cuenta.
    usage: tuple[int, int] | None = None
    model: str | None = None


class LLM(Protocol):
    async def chat(
        self, *, messages: list[dict], tools: list[dict], model: str
    ) -> LLMResponse: ...


def _has_key() -> bool:
    from app.services.secret_service import get_secret

    return bool(get_secret("anthropic_api_key") or get_secret("openai_api_key"))


def reasoning_kwargs() -> dict[str, Any]:
    """Esfuerzo de razonamiento (gpt-5.x / gpt-6 Luna/Sol). En Chat Completions, las
    herramientas del agente solo funcionan con "none". LiteLLM aún no conoce los modelos
    más nuevos, así que se le permite pasar el parámetro explícitamente."""
    if not settings.llm_reasoning_effort:
        return {}
    return {
        "reasoning_effort": settings.llm_reasoning_effort,
        "allowed_openai_params": ["reasoning_effort"],
    }


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

        from app.services.secret_service import get_secret

        qualified = _qualify(model)
        kwargs: dict[str, Any] = {"model": qualified, "messages": messages}
        kwargs.update(reasoning_kwargs())
        # LiteLLM lee la key del ENTORNO del proceso: para que una rotación guardada
        # en la app aplique de inmediato, se pasa explícita por llamada (feature 017).
        key_name = "anthropic_api_key" if qualified.startswith("anthropic/") else "openai_api_key"
        if api_key := get_secret(key_name):
            kwargs["api_key"] = api_key
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
        u = getattr(resp, "usage", None)
        usage = (
            (int(getattr(u, "prompt_tokens", 0) or 0), int(getattr(u, "completion_tokens", 0) or 0))
            if u is not None
            else None
        )
        return LLMResponse(content=msg.content, tool_calls=calls, usage=usage, model=model)


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

    extra = reasoning_kwargs()
    response = await litellm.acompletion(
        model=_qualify(settings.llm_model),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        **extra,
    )
    return response.choices[0].message.content or ""
