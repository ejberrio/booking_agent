<!-- SPECKIT START -->
Feature activa: **021-language-selector** (es/en/pt; issue #124).
Plan: `specs/021-language-selector/{plan,research,data-model,quickstart}.md` + `contracts/preferences-api.md`.
Diseño: i18n propia sin librerías — `apps/web/lib/i18n/{es,en,pt}.ts` (es = referencia; en/pt tipados
`Messages = typeof es` → texto faltante rompe tsc/build), `I18nProvider`/`useI18n()` {lang, setLang, t, fmt}
con Intl es-CO/en-US/pt-BR y moneda COP. Preferencia: cookie `lang` (login sin sesión) + `app_preference`
(fila única, migración `b5c6d7e8f9a0`) vía GET/PUT /preferences (todos los dispositivos). Mensajes del
servidor siguen en español; la web los traduce con `lib/i18n/server-messages.ts` (exactos + patrones),
sin match → español. Factores de sugerencias con campos estructurados aditivos (relevance, days, adr,
samples, weight, state) → la web arma la frase por idioma; nombres de eventos intactos. Chat:
`language` en el request → instrucción al final del system prompt. Contenido del host/terceros nunca
se traduce. Sin cambios de comportamiento.
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
