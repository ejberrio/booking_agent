<!-- SPECKIT START -->
Feature activa: **014-calendar-suggestions** (sugerencias en el calendario + acción única
"Aprobar y aplicar"; issue #95). Plan y artefactos: `specs/014-calendar-suggestions/plan.md`,
`research.md`, `data-model.md`, `contracts/suggestions-api.md`, `quickstart.md`.
Diseño (R1-R6): la acción combinada ES `POST /suggestions/{id}/apply` reforzado — hoy ya publica y
transiciona directo a `applied` pero SIN validar estado (bug latente de doble aplicación) ni recortar
días pasados. Se añade: estados de entrada `proposed|approved` (otro ⇒ 409 honesto con estado real),
recorte `effective_from=max(date_from,hoy)` (todo pasado ⇒ 409 "vencida"), respuesta + `applied_from`,
fallo de canal ⇒ SyncIssue + sin commit (sigue `proposed`) + 502. `reject` acepta también `approved`
(simetría) y unifica 400→409. Ruta `approve` RETIRADA (consumidor único: botón web que desaparece;
`suggestion_service.approve` y el estado `approved` se conservan). Calendario: marcado client-side
(query `["suggestions"]` compartida; vigente = `proposed` && `date_to>=hoy`); `PriceCalendar` gana prop
opcional `suggestionDates: Set<string>` (punto violeta + leyenda); resolución en panel lateral nuevo
`SuggestionPanel` (sugerido vs actual, rango, confianza %, racional, botones; N sugerencias/día;
toasts con `detail` del server; invalida `["suggestions"]`+`["calendar"]` siempre). Lista: 2 botones.
Sin migraciones. 174 tests deben seguir verdes. Features 001-013 + #97 en `main`, PRODUCCIÓN (v0.1.2).
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
