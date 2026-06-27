<!-- SPECKIT START -->
Feature activa: **007-production-deploy** (Railway web+api + Neon Postgres; Fase 7).
Plan e artefactos: `specs/007-production-deploy/plan.md`, `research.md`, `data-model.md`,
`contracts/{environment,health,web-api-proxy}.md`, `quickstart.md`.
Decisiones clave: web pública + API en red privada (proxy Next, sin CORS); Neon SSL normalizado
para asyncpg/alembic; migraciones al arrancar; /health verifica DB; cron diario de scan; CD al push a main.
Backend Fases 1-6 en `main` (001…006) + integración real Beds24 (lecturas V1 + escritura V2).
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
