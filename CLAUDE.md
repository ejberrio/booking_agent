<!-- SPECKIT START -->
Feature activa: **024-floating-chat** (chat flotante desde cualquier pantalla; issue #127).
Plan: `specs/024-floating-chat/{plan,research,data-model,quickstart}.md` + `contracts/chat-history-api.md`.
Diseño: `ChatProvider` (contexto) en `app/(app)/layout.tsx` compartido por la sección Chat y el panel flotante;
id de conversación en localStorage + historial desde `GET /chat/conversations` y `GET /chat/conversations/{id}`
(solo user/assistant, `pending_action_id`); panel superpuesto a la derecha (360–720 px, recordado), pantalla
completa en móvil, Ctrl+K/⌘K y Esc; tras `applied` se invalidan las consultas. Sin migraciones ni dependencias.
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
