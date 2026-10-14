<!-- SPECKIT START -->
Feature activa: **028-guest-privacy** (privacidad de huéspedes, Ley 1581; issue #145, épica #156 Comercial F0).
Plan: `specs/028-guest-privacy/{plan,research,data-model,quickstart}.md` + `contracts/privacy-api.md`.
Decisiones del host (2026-10-14): el anfitrión ve el nombre del huésped, el administrador nunca; nombre borrado 1 año tras la salida;
aceptación obligatoria y versionada de Términos y Privacidad (puerta en el servidor). TRA/SIRE en #167.
Anterior: 026-multitenant-accounts (cuentas aisladas, principio VI de la constitución v1.1.0).
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
