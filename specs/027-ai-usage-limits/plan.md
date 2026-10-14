# Implementation Plan: Uso y límites de IA por cuenta

**Branch**: `027-ai-usage-limits` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

## Summary

Tabla `ai_usage` (por cuenta, día, tipo y modelo) alimentada por **envoltorios medidores** del puerto LLM y del puerto de búsqueda (`MeteredLLM`, `MeteredSearch`) que se instalan donde se usa la IA: rutas del chat (tipo `chat`) y recorrido del cron por cuenta (tipo `scan`). El LLM devuelve ahora los tokens de cada llamada. Límites en `account` (`chat_limit_month`, `search_limit_day`; NULL = valores por defecto de configuración). El chat consulta el uso del mes antes de llamar a la IA; el cron limita las búsquedas. Panel de administrador y tarjeta del anfitrión.

## Technical Context

Python 3.12 / FastAPI / SQLAlchemy async; Next.js 15. Sin dependencias nuevas. Precios en `settings.ai_prices` (JSON por variable de entorno `AI_PRICES`) con valores por defecto.

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ spec con decisiones del host, plan, contrato, tareas |
| II. Provider-agnostic | ✅ medición en envoltorios de los puertos `LLM` y `SearchProvider`, no en LiteLLM/Tavily |
| III. Human-in-the-loop | ✅ con acción pendiente el chat no se bloquea (la confirmación siempre se atiende) |
| IV. Pruebas | ✅ medición, límite, excepción por pendiente, tope de búsquedas, panel, aislamiento |
| V. Simplicidad | ✅ una tabla, dos columnas, sin planes ni cobro (#152) |
| VI. Aislamiento | ✅ `ai_usage` es `AccountOwned`; el panel de plataforma vive en `admin_service` |

## Source Code

```text
apps/api/app/llm/client.py               # LLMResponse.usage (tokens) y model
apps/api/app/core/config.py              # ai_prices, ai_chat_limit_month, ai_search_limit_day
apps/api/app/models/usage.py             # AIUsage (AccountOwned)
apps/api/app/models/account.py           # chat_limit_month, search_limit_day
apps/api/app/services/usage_service.py   # record, month/day totals, limits, Metered*
apps/api/app/api/routes/chat.py          # límite + MeteredLLM; quota en la respuesta
apps/api/app/api/routes/account.py       # GET /account/usage
apps/api/app/api/routes/admin.py         # GET /admin/usage, PATCH /admin/accounts/{id}/limits
apps/api/app/services/admin_service.py   # agregados de plataforma
apps/api/scripts/scan_daily.py           # Metered* por cuenta; market_factory(session, search, llm)
apps/api/migrations/versions/d4e5f6a7b8c0_ai_usage.py
apps/api/tests/test_ai_usage.py
apps/web: components/account/usage-card.tsx, admin "Uso de IA", aviso en el chat, i18n usage.ts
```

## Delivery

Un PR → staging (el host prueba con un límite bajo en su cuenta de staging) → copia de Neon → producción.
