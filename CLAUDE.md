<!-- SPECKIT START -->
Feature activa: **009-booking-offers** (v1 LIGERA: claridad del agente + sección "Ofertas" con deep-links).
Plan e artefactos: `specs/009-booking-offers/plan.md`, `research.md`, `data-model.md`,
`contracts/{offers-page,agent-guidance}.md`, `quickstart.md`.
HALLAZGO clave (research, verificado en vivo): la API de Beds24 V2 **NO gestiona los deals de Booking**
(ni crear ni listar; se gestionan en el dashboard de Beds24 / extranet). → v1 NO sincroniza; entrega
claridad del agente (deals visibles se gestionan fuera + enlace; distinguir de la promoción de precio
interna) + página informativa "Ofertas" con deep-links. Sin entidades ni endpoints nuevos.
App YA EN PRODUCCIÓN (Railway web+api + Neon, CD). Features 001-008 en `main`.
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
