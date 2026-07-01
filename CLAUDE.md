<!-- SPECKIT START -->
Feature activa: **010-observability** (Sentry errores + logging estructurado + endpoint /status).
Plan e artefactos: `specs/010-observability/plan.md`, `research.md`, `data-model.md`,
`contracts/{status-endpoint,error-tracking,request-logging}.md`, `quickstart.md`.
Decisiones: Sentry (sentry-sdk[fastapi] + @sentry/nextjs vía instrumentation, sin withSentryConfig),
NO-OP sin DSN, send_default_pii=False, 0% trazas; logging por petición en líneas key=value (path sin
query); /status (protegido) con version/db/beds24(cacheado ~5min)/open_issues, resiliente; /health se
mantiene. Sin entidades/migraciones. Variables: SENTRY_DSN, NEXT_PUBLIC_SENTRY_DSN, LOG_LEVEL.
App YA EN PRODUCCIÓN (Railway web+api + Neon, CD). Features 001-009 en `main`.
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
