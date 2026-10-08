<!-- SPECKIT START -->
Feature activa: **019-actionable-suggestions** (sugerencias accionables).
Plan: `specs/019-actionable-suggestions/{plan,research,data-model,quickstart}.md` +
`contracts/suggestions-batch-api.md`. Decisiones del host (2026-10-08): bloques POR EVENTO/PERIODO;
SELECCIÓN MÚLTIPLE con una vista previa + una confirmación; mantener sugerencias a la baja.
Diseño: noches vendibles derivadas al consultar (futuras, sin reserva confirmada, sin bloqueo,
sin inventario 0) → la pestaña oculta ocupadas y reaparecen al cancelar; `app/domain/suggestion_blocks.py`
PURO (event:<nombre> une días no contiguos; period:<kind> solo contiguos); `services/suggestion_batch.py`
con preview (huella sha256 de ids + fecha|sugerencia|antes|después|válida|motivo) y apply por tramos
contiguos de igual precio en SAVEPOINT (fallo de publicación → rollback del tramo + SyncIssue, la
sugerencia sigue pendiente; applied solo con ≥1 aplicada y 0 fallidas). Engine: la equivalente
pendiente refresca rationale/confidence. SIN migraciones. Calendario y apply individual (014) intactos.
Fuera de alcance: editar precio, rechazar en bloque, aplicar todo, webhooks (#117).
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
