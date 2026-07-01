# Tasks: Gestión de promociones de precio vía API

**Feature**: 011-api-promotions · **Branch**: `011-api-promotions`
**Input**: [spec.md](spec.md) · [plan.md](plan.md) · [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md)

Convenciones: `[P]` = paralelizable (archivos distintos, sin dependencias pendientes). Rutas relativas a la raíz del repo. Tests en los límites (adapter, pricing, validaciones) por Principio IV de la constitución.

---

## Phase 1: Setup

- [X] T001 Añadir `beds24_promo_offer_id: int | None = None` a `apps/api/app/core/config.py` (oferta designada; documentar en `.env.example`).
- [X] T002 [P] Añadir `PromotionStatus` (draft/publishing/published/sync_error/retiring/retired) a `apps/api/app/models/enums.py`.

## Phase 2: Foundational (bloquea todas las historias)

- [X] T003 Crear el modelo `Promotion` en `apps/api/app/models/promotion.py` (campos de data-model: unit_type_id, offer_id, external_id, name, first_night, last_night, base_price, price, discount_pct, min_nights, status, timestamps) y registrarlo en `apps/api/app/models/__init__.py`.
- [X] T004 Generar migración Alembic para `promotion` + enum `promotionstatus` (patrón `postgresql.ENUM(create_type=False)`), encadenada tras `7d3816a7c205`, en `apps/api/alembic/versions/`.
- [X] T005 [P] Añadir el tipo `RemoteFixedPrice` y los métodos del puerto (`set_fixed_price`, `get_fixed_prices`, `disable_fixed_price`, `get_offers`) a `apps/api/app/channels/base.py` (contract: [channel-fixedprices.md](contracts/channel-fixedprices.md)).
- [X] T006 [P] Crear los esquemas Pydantic en `apps/api/app/schemas/promotion.py`: `PromotionCreate`, `PromotionPreview`, `PromotionView`, `PromotionApplyResult`, `PromotionRetire` + helper `promotion_fingerprint` (contract: [promotions-api.md](contracts/promotions-api.md)).
- [X] T007 Implementar en `apps/api/app/channels/beds24_v2.py` los métodos del puerto: `set_fixed_price` (POST /inventory/fixedPrices, crear=sin id, extraer `id`→external_id), `get_fixed_prices` (GET), `disable_fixed_price` (POST con id + roomPriceEnable=false), `get_offers` (GET /inventory/rooms/offers con arrival/departure/numAdults). Clasificar errores y redactar secretos como el resto del adapter.
- [X] T008 [P] Test del adapter en `apps/api/tests/test_beds24_v2_promotions.py` con `httpx.MockTransport`: crear (devuelve external_id), leer lista, neutralizar (roomPriceEnable=false), y clasificación de error (ChannelError sin filtrar token).
- [X] T009 Añadir a `apps/api/app/services/sync_service.py` `publish_promotion` y `retire_promotion` (envuelven set/disable del adapter; ante fallo crean `SyncIssue`; best-effort, no relanzan).

**Checkpoint**: modelo, migración, puerto+adapter y publicación resiliente listos → las historias pueden implementarse.

---

## Phase 3: User Story 1 — Crear una promoción (Priority: P1) 🎯 MVP

**Meta**: crear una promo (precio+fechas+estancia mínima opcional) por chat y calendario, con preview→confirm→publish→auditar.
**Test independiente**: pedir una promo para un rango, ver propuesta coherente (base, precio con descuento, ahorro, %), confirmar y verla publicada.

- [X] T010 [US1] Crear `apps/api/app/services/promotion_service.py` con `preview(...)`: resuelve la oferta designada (config), obtiene `base_price` del calendario (adapter `get_rates`), calcula `price` desde `discount_pct` (o valida `price`), redondeo COP, arma `PromotionPreview` con `saving`, `warnings` y `fingerprint`.
- [X] T011 [US1] Añadir a `promotion_service` las validaciones (FR-005): `price>0`, `price<base`, `pct∈(0,100)`, rango válido/no pasado, `min_nights≥1`, y detección de **solape** (por offer+fechas en BD) → warning que exige `confirm_overlap`. Guarda inválidos con `ValueError` (mensaje claro para el loop del agente).
- [X] T012 [US1] Añadir `apply(...)` a `promotion_service`: valida fingerprint, persiste `Promotion` (status→publishing), llama `sync_service.publish_promotion`, guarda `external_id`, status→published/sync_error, registra `AgentAction` (antes/después, origen).
- [X] T013 [US1] Endpoints en `apps/api/app/api/routes/pricing.py`: `POST /pricing/promotions/preview` y `POST /pricing/promotions/apply` (contract [promotions-api.md](contracts/promotions-api.md); 400 validación, 409 fingerprint obsoleto, 200 con sync_error).
- [X] T014 [P] [US1] Tool del agente `propose_create_promotion` (real) en `apps/api/app/agent/tools.py` + `build_proposal`/`apply_proposal` para promociones (usa `promotion_service`).
- [X] T015 [P] [US1] Reglas en `apps/api/app/agent/prompts.py`: una promo = precio+fechas(+min_nights) sobre la oferta designada; % → calcula precio; **distinguir** de "deal nativo de Booking" (FR-012); interpretar rangos relativos (reutiliza patrón fecha actual).
- [X] T016 [US1] Feedback de validación (`ValueError`) para las nuevas tools en `apps/api/app/agent/orchestrator.py`.
- [X] T017 [P] [US1] Tests en `apps/api/tests/test_promotion_service.py`: cálculo de descuento %, precio absoluto, redondeo, todas las validaciones y el solape.
- [X] T018 [P] [US1] Test en `apps/api/tests/test_agent_promotions.py`: proponer creación (chat) genera propuesta; guardas de precio≤0/≥base; no confunde con deal nativo.
- [X] T019 [P] [US1] Web: acción "Crear promoción" desde el rango del calendario en `apps/web/components/calendar/range-editor.tsx` (o componente hermano) + llamada a `/pricing/promotions/preview|apply` en `apps/web/lib/api.ts` y tipos en `apps/web/lib/types.ts`.

**Checkpoint**: US1 entrega el MVP — se puede lanzar una oferta real sin entrar al panel.

---

## Phase 4: User Story 2 — Ver promociones y su estado (Priority: P1)

**Meta**: listar promociones (oferta, fechas, precio, ahorro, estado) por chat y UI.
**Test independiente**: consultar y comprobar que coincide con el canal y refleja incidencias.

- [X] T020 [US2] `list_promotions(unit_type_id)` en `promotion_service`: combina BD (metadatos: %, estado, auditoría) con verificación de publicación; calcula `saving`; señala `sync_error`.
- [X] T021 [US2] Endpoint `GET /pricing/promotions?unit_type_id=` en `apps/api/app/api/routes/pricing.py` → `{promotions: PromotionView[]}`.
- [X] T022 [P] [US2] Tool del agente `get_promotions` en `apps/api/app/agent/tools.py` (+ mención en prompts para responder "¿qué promociones tengo?").
- [X] T023 [P] [US2] Web: evolucionar `apps/web/app/(app)/offers/page.tsx` (de solo deep-links, feature 009) a **lista real** de promociones con oferta/fechas/precio/ahorro/estado y estado vacío con guía.
- [X] T024 [P] [US2] Test en `apps/api/tests/test_promotion_service.py`: `list_promotions` (estado vacío, published, sync_error, saving correcto).

**Checkpoint**: US1+US2 = crear y verificar; incremento desplegable.

---

## Phase 5: User Story 3 — Editar o retirar una promoción (Priority: P2)

**Meta**: editar (fechas/precio/estancia) y retirar (neutralizar+ocultar), con preview→confirm→auditar.
**Test independiente**: sobre una promo existente, cambiar precio/fechas y retirarla; verificar efecto en el canal y auditoría antes/después.

- [X] T025 [US3] `edit(...)` en `promotion_service`: reusa `apply` con `id` presente → modifica el mismo `external_id` (POST con id), re-valida, registra `AgentAction` antes/después.
- [X] T026 [US3] `retire(id, confirm)` en `promotion_service`: llama `sync_service.retire_promotion` (disable_fixed_price → roomPriceEnable=false), status→retired, oculta de activas, audita. Maneja sync_error.
- [X] T027 [US3] Endpoint `POST /pricing/promotions/retire` en `apps/api/app/api/routes/pricing.py` (edit va por `apply` con `id`).
- [X] T028 [P] [US3] Tools del agente `propose_edit_promotion` y `propose_retire_promotion` en `apps/api/app/agent/tools.py` + reglas en `prompts.py`.
- [X] T029 [P] [US3] Web: acciones editar/retirar en `apps/web/app/(app)/offers/page.tsx` (con confirmación).
- [X] T030 [P] [US3] Tests en `apps/api/tests/test_promotion_service.py` y `test_agent_promotions.py`: editar (modifica external_id), retirar (neutraliza + oculta), auditoría antes/después, retirada reversible.

**Checkpoint**: ciclo de vida completo.

---

## Phase 6: Polish & Cross-Cutting

- [X] T031 [P] ADR `docs/adr/0003-api-promotions.md`: hallazgo (V2 escribe fixedPrices/offers), corrección de la conclusión de la Feature 009, decisiones D1–D8.
- [X] T032 [P] Documentar en `docs/operations.md`: oferta designada (`BEDS24_PROMO_OFFER_ID`, enable=always), verificación de escritura acotada/reversible y la limpieza manual del registro neutralizado (no hay DELETE).
- [X] T033 Ejecutar `uv run ruff check` + `uv run pytest` (apps/api) y `npm run build` + lint (apps/web); dejar verde.
- [X] T034 Validar el flujo de [quickstart.md](quickstart.md) (crear/ver/editar/retirar) y —con confirmación del host— la verificación de escritura real acotada contra el canal.

---

## Dependencias y orden

- **Setup (T001–T002)** → **Foundational (T003–T009)** → historias.
- **US1 (T010–T019)** es el MVP; **US2 (T020–T024)** y **US3 (T025–T030)** dependen de Foundational y de partes de US1 (servicio/endpoints base) pero son incrementos independientes entre sí.
- **Polish (T031–T034)** al final.

## Paralelización (ejemplos)

- Foundational: T005 (puerto) ∥ T006 (esquemas) ∥ T008 (test adapter, tras T007).
- US1: T014 (tool) ∥ T015 (prompts) ∥ T017/T018 (tests) ∥ T019 (web) una vez existe el servicio (T010–T012).
- Polish: T031 (ADR) ∥ T032 (docs).

## MVP

Setup + Foundational + **US1** = poder crear y publicar una promoción real desde la app. US2 (ver) se recomienda junto al MVP para verificar; US3 (editar/retirar) es el siguiente incremento.
