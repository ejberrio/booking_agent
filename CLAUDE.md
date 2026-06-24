<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
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
