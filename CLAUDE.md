<!-- SPECKIT START -->
Feature activa: **023-extend-prices** (extender precios hacia el futuro; issue #126).
Plan: `specs/023-extend-prices/{plan,research,data-model,quickstart}.md` + `contracts/extension-api.md`.
Hallazgo (2026-10-08): en Beds24 solo hay precio hasta 2027-02-12; desde el 13-feb las noches están sin precio y
cerradas (numAvail 0). Decisiones del host: plantilla mensual editable (mediana del mismo mes sin eventos, si no la
global; % opcional viernes/sábado), horizonte por defecto hoy+18 meses (máx. 24), abrir las noches cerradas sin
precio salvo las bloqueadas por el host desde la app. Diseño: preview lee el calendario remoto; apply por mes en
SAVEPOINT con `set_calendar_entries` (1 POST + 1 GET); auditoría `ChangeOrigin.extension`; aviso < 12 meses en
panel y calendario; precio ≤ 0 = sin precio (migración `d7e8f9a0b1c2` borra filas basura).
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
