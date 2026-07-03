<!-- SPECKIT START -->
Feature activa: **013-channel-pricing** (precios y promociones por canal; issue #88).
Plan e artefactos: `specs/013-channel-pricing/plan.md`, `research.md`, `data-model.md`,
`contracts/{channel-manager-port,pricing-api,agent-tools}.md`, `quickstart.md`.
Hallazgos EN VIVO (2026-07-02): (R1) el ajuste % por canal se materializa en el **multiplier del
canal** vía `POST /channels/settings` (Alpha; string componible: `*[CONVERT:COP-USD]` + 8% ⇒
`*[CONVERT:COP-USD]*1.08`; el prefijo del operador es INTOCABLE; verificar con re-GET). Soportado
solo para airbnb (booking vende a precio base — honestidad). (R2) los fixed prices SÍ se limitan
por canal: campo `channels: {airbnb: {enable: bool}, ...}` (⚠️ clave real `enable`, el yaml dice
`enabled`). Diseño: puerto neutro `get/set_channel_price_adjustment(channel, factor: Decimal)` +
`supports_price_adjustment`; `RemoteFixedPrice.channels: dict[str,bool]|None`; servicio nuevo
`channel_pricing_service` (preview→confirm(fingerprint)→apply→audit AgentAction→verify re-GET,
fallo ⇒ SyncIssue sin persistir); rango offset [−50,+100]; `Channel.price_offset_pct` se ACTIVA
(0 migraciones); scope de promos en `Promotion.conditions["channels_scope"]` (None=todos, []=inválido);
endpoints `GET/POST /pricing/channel-offsets(/preview|/apply)` + `channels_scope` en promotions;
tools `get_channel_offsets`/`propose_channel_offset`; web: tarjeta "Precio por canal" en Configuración,
alcance+deep-links Airbnb en Ofertas. Precio efectivo = base×(1+pct/100) (el CONVERT es neutro en
valor). ADR 0004. Features 001-012 en `main`, app EN PRODUCCIÓN (v0.1.2).
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
