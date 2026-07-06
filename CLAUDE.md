<!-- SPECKIT START -->
Feature activa: **017-secrets-ui** (gestión de secretos desde Configuración; issue #99, SENSIBLE).
Plan y artefactos: `specs/017-secrets-ui/plan.md`, `research.md`, `data-model.md`,
`contracts/secrets-api.md`, `quickstart.md`. ADR 0005 pendiente de escribir en implement.
Diseño (R1-R6): `secret_service` con CACHÉ en memoria de módulo — `get_secret(name)` SÍNCRONO
(consumidores incluyen get_adapter que es sync): caché(BD) > settings.env; carga en lifespan de la
API (try/except resiliente: BD caída → caché vacía, todo por env) y al inicio de scan_daily;
write-through en PUT/DELETE (rotación inmediata API; scan en su próxima corrida). Cifrado FERNET
(`cryptography>=43` DEP NUEVA), clave = urlsafe_b64(sha256(SECRET_KEY)); InvalidToken → estado
"unreadable" + fallback env (nunca rompe arranque). CRÍTICO LiteLLM: lee la key del ENTORNO → hay
que pasar `api_key=get_secret(...)` POR LLAMADA en LiteLLMClient.chat (prefijo anthropic/ →
anthropic_api_key, si no openai_api_key); `_has_key()` → get_secret. Tavily api_key y
get_adapter refresh_token → get_secret. Lista CERRADA: openai_api_key, anthropic_api_key,
search_api_key, beds24_refresh_token. Tablas `secret_entry` (name UNIQUE, value_encrypted Text,
hint String(8) últimos 4 — vacío si valor <8 chars) y `secret_change_log` (action String(12)
set|deleted, sin enum BD); migración `e2f3a4b5c6d7` (down d1e2f3a4b5c6). Endpoints
`/settings/secrets` (GET estado enmascarado, PUT {value} sin eco, DELETE, POST /{name}/test —
LLM max_tokens=1 / search 1 result / beds24 test_connection, detail FIJO categorizado, GET /audit).
NUNCA valores en respuestas/logs/auditoría — test centinela SC-002 obligatorio. El agente NO gana
tools de secretos. Sin re-confirmación de password (documentado en spec). Web: tarjeta en
Configuración (write-only, campo se limpia tras guardar, Probar inline, aviso del scan).
210 tests deben seguir verdes. Features 001-016 + #97 en `main`, PRODUCCIÓN.
<!-- SPECKIT END -->

# Booking AI Agent

Plataforma single-tenant para gestionar precios/promociones de Booking.com con un agente de IA.

## Arquitectura
- Monorepo: `apps/web` (Next.js + TS + Tailwind + shadcn) y `apps/api` (FastAPI + SQLAlchemy + LiteLLM). Postgres vía `docker-compose`.
- Booking.com se integra **vía Channel Manager** (adaptador provider-agnostic), no API directa. Ver `docs/adr/0001-arquitectura.md`.
- LLM multi-proveedor (LiteLLM), configurable. Principios en `.specify/memory/constitution.md`.

## Comandos
- `make setup` — instala deps (api: `uv sync`, web: `npm install`)
- `make api` / `make web` — corre API (:8000) / web (:3000)
- `make test` — `uv run pytest` en la API
- `make lint` — ruff + next lint

## Convenciones
- Spec-Driven: features con `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.
- Escrituras de precio siempre con confirmación + audit log (principio III, no negociable).
- Integraciones (Channel Manager, LLM, búsqueda) detrás de interfaces; nada propietario en el dominio.
- Planificación en GitHub Project #1 (milestones = Fases 1–7).
