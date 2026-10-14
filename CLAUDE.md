<!-- SPECKIT START -->
Feature activa: **029-offline-mode** (modo sin conexión: apartamento manual, iCal, aplicar a mano; issue #146).
Spec/tareas: `specs/029-offline-mode/{spec,tasks}.md`. `account.channel_mode` (connected|manual) → `ManualChannelAdapter`;
`manual_service`, `ical_service` (lista blanca de dominios), rutas `/manual/*`. Anteriores: 032 (asistente en bloque),
027 (límites de IA), 028 (Ley 1581), 026 (principio VI).
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
