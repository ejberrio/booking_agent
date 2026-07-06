<!-- SPECKIT START -->
Feature activa: **018-suggestion-engine-v2** (motor de sugerencias v2; issue #98, LA GRANDE).
Plan: `specs/018-suggestion-engine-v2/{plan,research,data-model,quickstart}.md` +
`contracts/engine-v2-api.md`. Clarify del host: agrupación POR EVENTO/RANGO; tope bajista −15%
(piso min_price); POIs semilla Daviarena (sep-nov 2026) + CC Mayorca; ventana hueco 14 días.
Diseño: Property + address/lat/lon (schema Beds24 los trae en GET /properties; RemoteProperty
extendido; import upsert); POI table (name, note, fechas nullable, is_active) + ScanConfig fila
única (zone, queries_per_scan=12, event_kinds); MarketReference + occupancy_pct/sample_size;
SuggestionStatus + `superseded` (PG ADD VALUE en autocommit_block; migración f3a4b5c6d7e8).
rationale JSONB retrocompatible: {text, factors[{kind: event|occupancy|gap|market, label, pct,
event?{name,location,dates,source_url}}], market{adr,samples,source}}. Motor: señales simétricas
(alcistas actuales + hueco ≤14d descuento progresivo, valle, mercado-ancla), agrupación por
(señal × rango contiguo × mismo precio base — cortar si el base cambia), reservas excluidas,
supersede al persistir (proposed solapadas → superseded; vencidas housekeeping; equivalentes no
se crean; primer scan depura las ~130). Puerto MarketDataProvider.get_snapshot(zone, month) →
MarketSnapshot|None; TavilyMarketProvider gratis (tarifas por LLM → MEDIANA + sample_size;
<3 muestras = confianza baja; 0 = None honesto); pago NO se construye (AirDNA API solo enterprise;
candidato real PriceLabs ~USD10/mes Colombia — ADR 0006). Rutas nuevas /pois CRUD +
GET/PUT /scan-config. Web: tarjetas POIs+Escaneo en Configuración; card/panel muestran factors
si existen (fallback text v1). apply/reject de superseded → 409 existente. 221 tests verdes.
Features 001-017 en `main`, PRODUCCIÓN (secretos verificados en prod, rotación real pendiente
del host T018).
Previa: 017-secrets-ui MERGEADA (PR #104, EN PROD; detalles en docs/adr/0005 y operations.md).
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
