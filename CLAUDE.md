<!-- SPECKIT START -->
Feature activa: **016-calendar-bookings-notes** (detalle de reservas + notas del host en el
calendario; issue #96). Plan y artefactos: `specs/016-calendar-bookings-notes/plan.md`,
`research.md`, `data-model.md`, `contracts/bookings-notes-api.md`, `quickstart.md`.
Diseño (R1-R6): `RemoteBooking.guest_name` campo ÚNICO neutro (V2 compone firstName+lastName del
schema oficial — verificado en apiV2.yaml; parciales OK, vacío → None; V1 → None). `Booking` +
columna `guest_name` String(200) nullable. Import: crear → set; existente → corrige solo si remoto
NO vacío ≠ local (silencio remoto nunca borra; cuenta updated_count, patrón 012). Entidad nueva
`CalendarNote` (unit_type_id FK, date_from/date_to NOT NULL from<=to, text ≤500 no vacío) en
models/calendar.py; migración `d1e2f3a4b5c6` (down c9d0e1f2a3b4). Endpoints nuevos: `GET /bookings?
unit_type_id&date_from&date_to` (confirmadas, solape [check_in,check_out), nights calculado, router
bookings.py) y CRUD `/calendar-notes` (SIN fingerprint — local, criterio 015; DELETE real; router
calendar_notes.py; registrar ambos en routes/__init__). Web patrón client-side (calendario NO se
toca): `PriceCalendar` + prop `noteDates` (punto LIMA + leyenda); panel único nuevo `DayInfoPanel`
(selección 1 día → sección Reservas: huésped o "sin nombre", canal, llegada→salida, noches, ref;
cualquier selección → sección Notas: cubren el rango + crear sobre TODA la selección + editar/
borrar). Privacidad: guest_name NUNCA en logs (middleware solo method/path/status); el tool del
agente NO gana el campo. Noche: día de salida NO ocupa. 199 tests deben seguir verdes.
Features 001-015 + #97 en `main`, PRODUCCIÓN (deals sembrados ids 1-3).
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
