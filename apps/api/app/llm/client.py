"""Capa LLM provider-agnostic.

Envuelve LiteLLM para poder cambiar de modelo/proveedor desde configuracion
(Fase 4: "Configuracion de LLM por UI"). Si no hay API key configurada,
funciona en modo demo para que el scaffold arranque sin credenciales.
"""

from app.core.config import settings

SYSTEM_PROMPT = (
    "Eres el asistente de pricing de un host en Booking.com. "
    "Ayudas a consultar y ajustar precios por dia, rango y promociones. "
    "Nunca apliques cambios sin confirmacion explicita del host."
)


def _has_key() -> bool:
    return bool(settings.anthropic_api_key or settings.openai_api_key)


async def complete(message: str) -> str:
    if not _has_key():
        return (
            "[modo demo: no hay API key de LLM configurada] "
            f"Recibi tu mensaje: '{message}'. "
            "Configura ANTHROPIC_API_KEY (o OPENAI_API_KEY) en .env para activar el agente."
        )

    import litellm

    model = settings.llm_model
    if settings.llm_provider and "/" not in model:
        model = f"{settings.llm_provider}/{model}"

    response = await litellm.acompletion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )
    return response.choices[0].message.content or ""
