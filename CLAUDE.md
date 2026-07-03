<!-- SPECKIT START -->
Feature activa: **015-calendar-offers** (calendario con promos + deals nativos visibles, registro
manual NativeDeal; issue #94). Plan y artefactos: `specs/015-calendar-offers/plan.md`, `research.md`,
`data-model.md`, `contracts/native-deals-api.md`, `quickstart.md`.
Diseño (R1-R6): la "advertencia de doble descuento" actual NO existe en el backend (solo guía web +
prompt) → warning NUEVO en `offer_promotion_service.preview` por cada NativeDeal activo que solape
fechas ∩ canal (scope None = todos; no bloquea) — protege web Y agente por el mismo cuello. Modelo
plano `native_deal` (channel enum ChannelKind reutilizado `create_type=False`, name ≤120,
discount_pct 0-100, date_from/date_to NULLABLE = extremos abiertos, ambos NULL = "siempre activo"
Airbnb semanal/mensual, is_active). Migración `c9d0e1f2a3b4` (down b7c8d9e0f1a2). Solape:
`(from IS NULL OR from<=last) AND (to IS NULL OR to>=first)`. CRUD `/pricing/native-deals`
(GET/POST/PATCH/DELETE, SIN fingerprint — registro local, cero llamadas al CM; DELETE real).
Calendario: patrón client-side 014 — `/pricing/calendar` NO se toca; web cruza GET native-deals +
GET /pricing/promotions existente (ya trae name/discount_pct/first-last_night/channels_scope);
`PriceCalendar` + prop `nativeDealDates` (punto CIAN + leyenda); panel nuevo `OffersPanel` (promos
app + deals del día); tarjeta CRUD en Ofertas; dashboard también marca. Semilla post-deploy con
confirmación del host: Vacaciones Julio·mín 3 (booking 20% jul 3-31), semanal 5% y mensual 25%
(airbnb, abiertos). 187 tests deben seguir verdes. Features 001-014 + #97 en `main`, PRODUCCIÓN.
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
