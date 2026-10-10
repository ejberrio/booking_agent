<!-- SPECKIT START -->
Feature activa: **026-multitenant-accounts** (multicliente mínimo; issue #143, épica #156 Comercial F0).
Plan: `specs/026-multitenant-accounts/{plan,research,data-model,quickstart}.md` + `contracts/accounts-api.md`.
Constitución v1.1.0: principio VI aislamiento por cuenta (NO NEGOCIABLE). Decisiones del host (2026-10-10): registro solo
con código de invitación (interruptor para abrirlo), correo+contraseña Y Google, un usuario por cuenta. Diseño: account_id
en todas las tablas del anfitrión + filtro automático del ORM (falla cerrado), sesiones opacas en la API (Bearer desde la
cookie sl_session), Resend para correos, Google con PKCE (app: navegador del sistema → APK 1.1.0), cuenta nº 1 reclamada
con la contraseña actual. Entrega en 4 PRs (PR1 aislamiento sin cambio visible → PR2 sesiones → PR3 invitaciones/admin → PR4 Google).
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
