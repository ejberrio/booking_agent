<!-- SPECKIT START -->
Feature activa: **012-multichannel-core** (núcleo multi-canal Booking.com + Airbnb vía Beds24; issue #87).
Plan e artefactos: `specs/012-multichannel-core/plan.md`, `research.md`, `data-model.md`,
`contracts/{channel-manager-port,status-api,agent-tools}.md`, `quickstart.md`.
Contexto: Airbnb YA conectado a Beds24 (issue #86, sync Prices & Availability). Hoy el import
etiqueta TODA reserva como `ChannelKind.booking` (hardcode en `sync_service.py`) y el prompt del
agente dice "solo el canal Booking". Decisiones: `RemoteBooking.channel: str | None` (token neutro;
Beds24 V2 lo da en `b["channel"]`, fallback `referer`); normalización en dominio booking/airbnb/
desconocido→direct (nunca aborta); corrección de históricos DENTRO del import (re-importar corrige
`channel_kind` de reservas existentes; dedupe por `external_ref` ⇒ 0 duplicados; SIN migración —
no hay cambios de esquema); canales activos por config `CHANNELS_ACTIVE` (default booking,airbnb);
`system_prompt(today, active_channels)`; tool `get_bookings` += filtro/salida `channel`;
`GET /status` += bloque `channels` (resiliente); dashboard web tarjeta "Canales" vía proxy.
Principio III intacto (feature de lectura/etiquetado). Features 001-011 en `main`, app EN PRODUCCIÓN.
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
