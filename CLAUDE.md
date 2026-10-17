<!-- SPECKIT START -->
Feature activa: **035-report-events** (consultar/reportar eventos: `event_report_service`, `/events`, herramientas `get_events`/`report_event`, spec `specs/035-report-events/spec.md`). Antes: **034-event-sources** (boleteras, agendas, festivos; área metropolitana en ambos sentidos).
Spec: `specs/034-event-sources/spec.md`. `event_sources_service` (TuBoleta, Ticketmaster CO, Plaza Mayor:
JSON-LD/API, robots.txt, sin evadir bloqueos, `EVENT_SOURCES_DISABLED`), `holidays_co` (Ley Emiliani),
`municipalities.area_keys` (+`colombia`), búsquedas dirigidas semanales. Anteriores: 033 (eventos del área),
030 (página pública), 029 (sin conexión), 032, 027, 028, 026 (principio VI).
<!-- SPECKIT END -->

# Booking AI Agent

Plataforma multicliente (cuentas aisladas, feature 026) para gestionar precios/promociones de Booking.com y Airbnb con un agente de IA.

## Arquitectura
- Monorepo: `apps/web` (Next.js + TS + Tailwind + shadcn) y `apps/api` (FastAPI + SQLAlchemy + LiteLLM). Postgres vía `docker-compose`.
- Booking.com se integra **vía Channel Manager** (adaptador provider-agnostic), no API directa. Ver `docs/adr/0001-arquitectura.md`.
- LLM multi-proveedor (LiteLLM), configurable. Principios en `.specify/memory/constitution.md`.
- Multicliente: `account_id` + filtro automático del ORM (`app/db/tenancy.py`, falla cerrado); la cuenta sale solo de la sesión. Ver `docs/adr/0007-multitenancy.md`.

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
