# Tasks: Calendario con promociones y deals nativos visibles + registro manual de deals

**Input**: Design documents from `/specs/015-calendar-offers/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/native-deals-api.md, quickstart.md

**Tests**: incluidos (Constitución IV: la lógica de solape alimenta la advertencia de doble descuento — puede costar dinero). Patrón: pytest + SQLite async; web `npm run build`.

**Organization**: por user story. Fase Foundational = modelo + migración (los usan todas las stories).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable · **[Story]**: US1 (registro CRUD), US2 (marcado calendario), US3 (panel del día), US4 (advertencia real), US5 (semilla)

## Path Conventions

Monorepo: `apps/api/` (FastAPI) y `apps/web/` (Next.js), según plan.md.

---

## Phase 1: Foundational (bloqueante para todas las stories)

- [X] T001 Añadir modelo `NativeDeal` en `apps/api/app/models/pricing.py` (channel Enum ChannelKind, name String(120), discount_pct Numeric(5,2), date_from/date_to Date nullable, is_active Boolean default true, TimestampMixin) y exportarlo donde el paquete de modelos lo requiera
- [X] T002 Crear migración `apps/api/migrations/versions/c9d0e1f2a3b4_native_deal.py` (down_revision `b7c8d9e0f1a2`; enum `channelkind` con `postgresql.ENUM(..., create_type=False)` — patrón de channel_offset_log; downgrade limpio)

**Checkpoint**: `uv run alembic upgrade head` (local) y tests existentes verdes.

---

## Phase 2: User Story 1 — Registrar los deals nativos (P1) 🎯 MVP

**Goal**: CRUD local completo (`/pricing/native-deals`) con validaciones honestas; cero llamadas al Channel Manager.

**Independent Test**: crear/listar/editar/desactivar/borrar por API con dobles; validaciones 422; ninguna operación toca el puerto CM.

- [X] T003 [US1] Crear `apps/api/app/services/native_deal_service.py`: `NativeDealError`; `list_deals` (orden channel, date_from NULLS FIRST, id); `create/update/delete` con validación (canal ∈ {booking, airbnb}, nombre no vacío, 0 ≤ pct ≤ 100, date_from ≤ date_to si ambos; update parcial acepta null explícito para abrir extremos); `find_overlapping(session, first, last, channels_scope)` con la semántica de data-model.md (extremos abiertos; scope None = cualquier canal; solo activos)
- [X] T004 [US1] Rutas en `apps/api/app/api/routes/pricing.py`: `GET /pricing/native-deals` (`{"deals": [...]}`), `POST` (200 con el deal), `PATCH /{id}`, `DELETE /{id}` (`{"deleted": true}`); 404 inexistente, 422 con `detail` claro (NativeDealError)
- [X] T005 [US1] Tests en `apps/api/tests/test_native_deals.py` (parte CRUD): crear con/sin fechas, listar ordenado, editar parcial (incl. abrir extremo con null), desactivar/reactivar, borrar, validaciones (canal inválido, nombre vacío, pct 150, fechas invertidas) — vía cliente ASGITransport (patrón test_suggestion_resolve)

**Checkpoint**: registro funcional end-to-end por API.

---

## Phase 3: User Story 4 — Advertencia de doble descuento real (P2, antes que la UI: mismo backend) 

**Goal**: `preview` de promociones advierte nombrando cada deal activo que solapa fechas ∩ canal; cero falsas alarmas.

**Independent Test**: preview con deal solapante → warning con nombre/canal/%; scope que excluye el canal del deal, deal inactivo o fechas fuera → sin warning nuevo; sin deals → warnings idénticos a los actuales.

- [X] T006 [US4] En `apps/api/app/services/offer_promotion_service.py` (preview): tras los warnings existentes, consultar `native_deal_service.find_overlapping(first_night, last_night, channels_scope)` y añadir un warning por deal: `"Puede duplicar descuento con el deal nativo '{name}' ({display canal}, {pct}%). Revísalo antes de confirmar."` (display: Booking.com/Airbnb); NO bloquea ni cambia `valid`
- [X] T007 [US4] Tests en `apps/api/tests/test_native_deals.py` (parte solape/preview): matriz de solape (cerrado×cerrado, siempre-activo, medio-abierto ambos lados, sin solape por fechas, sin solape por canal con scope, deal inactivo); preview de promoción con y sin deals (usar los dobles/seed del suite de promociones existente como referencia); FR-010: sin deals registrados, `warnings` byte-a-byte como antes

**Checkpoint**: protección real activa para web y agente (mismo preview); `uv run pytest -q` completo verde.

---

## Phase 4: User Story 2 — Marcado en el calendario (P1)

**Goal**: días con deal activo marcados con punto cian + leyenda, en Calendario y dashboard; convive con los 4 marcadores existentes; sin deals, render idéntico.

**Independent Test**: con un deal jul 3-31 y uno siempre-activo, el mes marca lo que corresponde; desactivar → desaparece; `npm run build` verde.

- [X] T008 [P] [US2] `apps/web/lib/types.ts` (+`NativeDeal`) y `apps/web/lib/api.ts` (+`listNativeDeals`, `createNativeDeal`, `updateNativeDeal`, `deleteNativeDeal`)
- [X] T009 [P] [US2] `apps/web/components/calendar/price-calendar.tsx`: prop opcional `nativeDealDates?: Set<string>` → punto cian (`bg-cyan-500`, title "Deal nativo") + entrada de leyenda condicional (patrón de `suggestionDates`)
- [X] T010 [US2] `apps/web/app/(app)/calendar/page.tsx`: query `["native-deals"]` (staleTime 60s), helper `dealCoversDay(deal, ymd)` (extremos abiertos), computar `dealsByDate`/`nativeDealDates` del mes visible (solo activos) y pasar la prop; `apps/web/app/(app)/page.tsx` (dashboard): misma query + prop en su PriceCalendar

**Checkpoint**: panorama visual completo.

---

## Phase 5: User Story 3 — Panel "Ofertas del día" (P2)

**Goal**: clic en un día en oferta → detalle de promos de la app (nombre, %, alcance) y deals (nombre, canal, %, vigencia/"siempre activo"); convive con SuggestionPanel.

**Independent Test**: día con promo+deal muestra ambos; día sin ofertas no muestra el panel.

- [X] T011 [P] [US3] Crear `apps/web/components/calendar/offers-panel.tsx`: recibe `date`, `promotions: Promotion[]` (de la app, ya con name/discount_pct/first_night/last_night/channels_scope) y `deals: NativeDeal[]`; secciones "Promociones de la app" y "Deals nativos" con los datos del contrato; "siempre activo" para rango abierto; sin acciones de escritura (informativo; los deals se gestionan en Ofertas)
- [X] T012 [US3] Integrar en `apps/web/app/(app)/calendar/page.tsx`: query `["promotions"]` (api.listPromotions existente; status ≠ retired), `promosByDate` por `first_night..last_night`; si la selección es un día con ofertas, renderizar `OffersPanel` en la columna lateral junto a los paneles existentes

**Checkpoint**: ver → entender sin salir del calendario.

---

## Phase 6: User Story 1b/5 — Gestión en la sección Ofertas + semilla (P1/P3)

**Goal**: tarjeta CRUD "Deals nativos registrados" en Ofertas, integrada con la guía; semilla de los 3 deals reales en prod.

**Independent Test**: alta/edición/interruptor/borrado desde la UI reflejados en lista y calendario; los 3 deals reales visibles tras la semilla.

- [X] T013 [US1] Tarjeta "Deals nativos registrados" en `apps/web/app/(app)/offers/page.tsx`: lista (canal con nombre display, nombre, %, vigencia o "siempre activo", switch activo), formulario de alta (canal, nombre, %, fechas opcionales), editar y borrar (confirmación simple), toasts con `detail` del server; enlazar con la guía existente ("cuando crees/quites un deal en el panel del canal, anótalo aquí")
- [ ] T014 [US5] Semilla EN PROD tras el deploy, CON CONFIRMACIÓN DEL HOST de los valores (quickstart.md): "Vacaciones Julio · mín 3" (booking, 20, 2026-07-03→2026-07-31), "Descuento semanal" (airbnb, 5, abierto), "Descuento mensual" (airbnb, 25, abierto); verificar calendario y advertencia real con un preview de prueba (sin aplicar)

---

## Phase 7: Polish & Cross-Cutting

- [X] T015 [P] Documentar en `docs/operations.md`: registro de deals nativos (qué es y qué NO es), advertencia real de doble descuento, y el flujo "creas el deal en el panel → lo anotas en la app"
- [X] T016 Verificación final: `cd apps/api && uv run pytest -q` + ruff, `cd apps/web && npm run build`; upgrade/downgrade de la migración en SQLite/local; revisar FR-010 (sin deals, todo idéntico)

---

## Dependencies & Execution Order

- **Foundational (T001-T002)** primero (modelo+migración).
- **US1 API (T003-T005)** → habilita US4, US2, US3, US6.
- **US4 (T006-T007)** solo depende de T003 (find_overlapping) — puede ir antes que toda la web.
- **US2 (T008-T010)**: T008 ∥ T009; T010 tras ambos.
- **US3 (T011-T012)** depende de US2 (queries/cruce por fecha ya montados).
- **T013** depende de T008; **T014** tras el deploy (merge) — requiere confirmación del host.

```
T001-T002 ─▶ T003-T005 ─┬▶ T006-T007 (advertencia)      ─┐
                        └▶ T008/T009 ─▶ T010 ─▶ T011-T012 ─┼▶ T013 ─▶ merge ─▶ T014 (semilla, host)
                                                           ┘
```

## Implementation Strategy

**MVP = Foundational + US1** (registro por API). Luego la advertencia (backend puro), luego la web en dos incrementos (marcado → panel → gestión). Una sola rama/PR (patrón del proyecto), commits por fase; la semilla T014 se hace en prod después del merge, con confirmación del host.
