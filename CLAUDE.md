<!-- SPECKIT START -->
Feature activa: **025-mobile-app** (app móvil Android primero; issue #140).
Plan: `specs/025-mobile-app/{plan,research,data-model,quickstart}.md` + `contracts/push-api.md`.
Decisiones del host (2026-10-09): Capacitor (WebView remoto de staylever.com), Android ya (APK sin Play Store),
iPhone cuando haya cuenta Apple; avisos de reservas (nueva/modificada/cancelada) y sugerencias nuevas vía FCM;
sesión 90 días en la app (User-Agent StayLeverApp/). Repo PÚBLICO: llave de firma y google-services.json solo como
secretos de GitHub (script del host); credencial FCM como secreto cifrado de la app. APK en GitHub Actions → Release.
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
