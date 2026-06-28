<!-- SPECKIT START -->
Feature activa: **008-availability-management** (bloquear/abrir disponibilidad por chat y calendario).
Plan e artefactos: `specs/008-availability-management/plan.md`, `research.md`, `data-model.md`,
`contracts/{availability-api,agent-tools,channel-availability}.md`, `quickstart.md`.
Decisiones clave: reutiliza el flujo propone→confirma→publica→audita de precios; CalendarDay.is_blocked
distingue bloqueo del host de reserva; nunca toca noches reservadas; set_availability_range en el puerto
(Beds24 V2 numAvail); nueva tabla AvailabilityChangeLog; calendario con estados (incluido en esta feature);
reversión = operación inversa (abrir deshace bloquear).
App YA EN PRODUCCIÓN (Railway web+api + Neon, CD en push a main). Fases 1-7 en `main`.
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
