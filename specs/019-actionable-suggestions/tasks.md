# Tasks: Sugerencias accionables

**Input**: Design documents from `/specs/019-actionable-suggestions/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/suggestions-batch-api.md, quickstart.md

**Tests**: incluidos (Constitución IV: aplicar precios en lote es lógica que mueve dinero).

**Organization**: Foundational = noches vendibles (las usan US1, US2 y US3). Luego US1 → US2 → US3 → US4. US1 y US2 son ambas P1; US2 depende de Foundational, no de US1.

## Format: `[ID] [P?] [Story] Description`

- **[Story]**: US1 (solo vendibles), US2 (lote con una vista previa), US3 (bloques), US4 (racional al día)

## Path Conventions

Monorepo `apps/api/` y `apps/web/`, según plan.md.

---

## Phase 1: Foundational (bloqueante)

- [X] T001 Crear `apps/api/app/services/suggestion_batch.py` con `async def occupied_nights(session, unit_type_id, date_from, date_to) -> dict[date, str]` (motivo `"reservada"` si hay `Booking` `confirmed` con check_in ≤ d < check_out; `"bloqueada"` si `CalendarDay.is_blocked`; `"reservada"` si `units_available == 0` sin bloqueo) usando UNA consulta de reservas y UNA de calendario por rango
- [X] T002 En `apps/api/app/services/suggestion_batch.py`: `async def pending_views(session, *, unit_type_id=None, today) -> list[SuggestionView]` — sugerencias `proposed|approved` con `date_to ≥ today`, cada una con `sellable_nights` (fechas ≥ hoy no ocupadas), `occupied_count`, `total_nights` y `current_price` por noche (`pricing_service.get_price`); dataclasses `SellableNight`/`SuggestionView` según data-model.md
- [X] T003 Tests en `apps/api/tests/test_suggestion_batch.py` (parte vendibles): reserva confirmada oculta sus noches y no el día de salida; reserva cancelada NO oculta; bloqueo oculta con motivo "bloqueada"; inventario 0 sin bloqueo oculta; noches pasadas excluidas; sugerencia 100 % ocupada → `sellable_nights` vacío

**Checkpoint**: 256 tests previos + nuevos verdes.

---

## Phase 2: User Story 1 — Solo veo lo que puedo vender (P1) 🎯 MVP

**Goal**: la pestaña lista solo noches vendibles y reaparecen al cancelarse una reserva.
**Independent Test**: escenario 1–2 de quickstart.md.

- [X] T004 [US1] Ruta `GET /suggestions/blocks` en `apps/api/app/api/routes/suggestions.py` (declarada ANTES de las rutas `/{suggestion_id}`): llama a `pending_views` + agrupación (en esta fase, cada sugerencia vendible es su propio bloque `period:other`; T012 activa la agrupación real) y devuelve `{blocks, hidden_occupied}` según el contrato
- [X] T005 [US1] Test de ruta en `apps/api/tests/test_suggestion_batch.py`: `GET /suggestions/blocks` excluye sugerencias 100 % ocupadas, recorta las parciales y reporta `hidden_occupied`; tras pasar la reserva a `cancelled`, la misma llamada vuelve a incluir las noches (sin scan)
- [X] T006 [P] [US1] Tipos y API web: `apps/web/lib/types.ts` (`SellableNight`, `SuggestionView`, `SuggestionBlock`, `BatchPreview`, `BatchResult`) y `apps/web/lib/api.ts` (`listSuggestionBlocks`, `previewSuggestionBatch`, `applySuggestionBatch`)

**Checkpoint**: la API ya filtra; la web se cablea en US3 (la página usa los bloques).

---

## Phase 3: User Story 2 — Aplicar varias de una vez (P1)

**Goal**: una vista previa y una confirmación para N sugerencias, resultado por noche.
**Independent Test**: escenarios 4–6 de quickstart.md (con canal falso en tests).

- [X] T007 [US2] En `apps/api/app/services/suggestion_batch.py`: `async def preview_batch(session, suggestion_ids, *, today) -> BatchPreview` — por noche de cada sugerencia: `valid` / `reason` (`pasada`, `reservada`, `bloqueada`, `fuera de límites` vía `violates_rule` con la regla activa, `sugerencia resuelta` si no está `proposed|approved` o no existe, `conflicto` si dos seleccionadas cubren la misma noche — se invalidan ambas); `fingerprint` sha256[:16] de ids ordenados + `fecha|sugerencia|antes|después|válida|motivo`
- [X] T008 [US2] En `apps/api/app/services/suggestion_batch.py`: `async def apply_batch(session, channel, suggestion_ids, fingerprint, *, today) -> BatchResult` — recalcula el preview; huella distinta → `BatchResult(stale=True)` sin escribir; noches válidas agrupadas en tramos contiguos de igual precio (mismo `unit_type_id`); por tramo `async with session.begin_nested()`: `pricing_service.set_base_price(..., origin=ChangeOrigin.suggestion, validate_rule=False)` + `pricing_app_service.publish_effective`; si `issues > 0` **o el tramo lanza cualquier excepción** (red, token) → rollback del savepoint, noches `failed`, `SyncIssue(kind=comm_error, entity_ref="suggestion-batch:<ids>")` fuera del savepoint; estado final por sugerencia: `applied` (≥1 aplicada ∧ 0 fallidas, `applied_change_id` = primer `PriceChangeLog` de esa sugerencia) · `pending` · `unchanged`
- [X] T009 [US2] Rutas `POST /suggestions/batch/preview` y `POST /suggestions/batch/apply` en `apps/api/app/api/routes/suggestions.py` (antes de `/{suggestion_id}`): 422 con lista vacía; 409 con `detail` "La vista previa cambió (precios, reservas o sugerencias); revísala de nuevo." si stale; commit al final; `adapter.aclose()` en finally
- [X] T010 [US2] Tests en `apps/api/tests/test_suggestion_batch.py` (parte lote, con `FakeCM`/`PromoFakeCM` existentes): preview lista antes/después y omisiones con motivo; huella cambia si cambia un precio, una reserva o el estado de una sugerencia (→ 409 sin escrituras); apply publica y audita con `origin=suggestion` y marca `applied`; fallo de publicación en un tramo (por incidencias Y por excepción del canal) → ese tramo revertido localmente (precio anterior), noches `failed`, sugerencia sigue `proposed`, los demás tramos aplicados; fuera de límites omitida; conflicto entre dos seleccionadas; apply individual (014) sigue verde
- [X] T011 [P] [US2] Web: `apps/web/components/suggestions/batch-preview-dialog.tsx` — muestra la vista previa (resumen: N noches, M omitidas; tabla fecha · bloque/evento de origen · antes → después con flecha ↑/↓ · motivo de omisión), botón "Confirmar y publicar" (deshabilitado si `valid_count == 0`), y tras aplicar el resultado por noche (aplicadas / omitidas / fallidas); 409 → mensaje y botón "Volver a previsualizar"

**Checkpoint**: lote funcional por API y diálogo listo.

---

## Phase 4: User Story 3 — Bloques por evento o periodo (P2)

**Goal**: la pestaña muestra bloques seleccionables.
**Independent Test**: escenario 3 de quickstart.md.

- [X] T012 [US3] Crear `apps/api/app/domain/suggestion_blocks.py` (PURO): `build_blocks(views) -> list[SuggestionBlock]` — clave `event:<nombre normalizado>` si la sugerencia tiene factor `event` (une días no contiguos), si no `period:<gap|occupancy|other>` uniendo solo noches contiguas; título (nombre del evento / "Libre próximo" / "Ocupación alta" / "Otras"), `date_from/date_to`, `nights` ordenadas, `suggestion_ids`, `direction` up/down/mixed; bloques ordenados por fecha; conectar en `GET /suggestions/blocks` (reemplaza el agrupado trivial de T004)
- [X] T013 [P] [US3] Tests de dominio en `apps/api/tests/test_suggestion_blocks.py`: mismo evento en días no contiguos → 1 bloque; huecos contiguos → 1 bloque y se corta con un día sin sugerencia; evento y periodo no se mezclan; sugerencias v1 sin factors → `other`; `direction` up/down/mixed; bajadas presentes (no se filtran)
- [X] T014 [US3] Web: `apps/web/components/suggestions/suggestion-block.tsx` — casilla del bloque (marca/desmarca todas sus sugerencias), título + rango + nº de noches + badge sube/baja, lista expandible de noches (fecha, actual → sugerido, %), casillas por sugerencia con la leyenda "N de M noches · K ya reservadas/bloqueadas" cuando `occupied_count > 0`, `Rationale` de cada sugerencia, y acciones individuales existentes (aplicar/rechazar una) para no perder el flujo 014
- [X] T015 [US3] Web: `apps/web/app/(app)/suggestions/page.tsx` — consume `listSuggestionBlocks`, estado de selección (Set de ids), barra fija "N sugerencias · M noches seleccionadas · Previsualizar" que abre `batch-preview-dialog`; tras aplicar invalida `suggestions`, `calendar`, `bookings`; textos vacíos: "No hay sugerencias para noches libres" (+ "X noches ocultas por estar reservadas o bloqueadas" si `hidden_occupied > 0`)

**Checkpoint**: flujo completo en la web.

---

## Phase 5: User Story 4 — Explicación siempre al día (P3)

- [X] T016 [US4] En `apps/api/app/services/suggestion_engine.py`: `_exists_equivalent` devuelve la fila (no solo el id); si su estado es `proposed|approved`, actualizar `rationale` (= `_rationale(out, snap)`) y `confidence` antes de conservarla; mantener `keep` con su id
- [X] T017 [US4] Test en `apps/api/tests/test_suggestion_engine.py`: equivalente pendiente con racional viejo → tras el scan mismo id/estado y racional nuevo; aplicada/rechazada conservan el racional original

---

## Phase 6: Polish & Cross-Cutting

- [X] T018 [P] `docs/operations.md`: sección "Sugerencias en lote (019)" — qué se oculta y por qué, bloques, vista previa única, 409 por cambios, fallos parciales y dónde ver incidencias
- [X] T019 Validación: `uv run ruff check . && uv run pytest -q` (API) y `npx tsc --noEmit && npm run build` (web); revisar que el calendario no cambió (`suggestionDates` sigue usando `listSuggestions("proposed")`)
- [X] T020 Verificación en producción tras el deploy (solo lectura): `GET /suggestions/blocks` vía `railway run` — sin noches del 9–12 oct, bloque único para eventos multi-fecha, `hidden_occupied` coherente; el apply real lo hace el host desde la web

---

## Dependencies & Execution Order

- Phase 1 (T001–T003) bloquea todo.
- US1 (T004–T006) y US2 (T007–T011) dependen solo de Phase 1; US2 no depende de US1 (T006 [P] comparte archivos web con nadie más en ese momento).
- US3: T012 depende de T002/T004; T014–T015 dependen de T006 y T011.
- US4 (T016–T017) es independiente (solo engine) y puede ir en paralelo con US2/US3.
- Polish al final.

## Parallel Opportunities

- T006 (web types/api) ‖ T007–T010 (API lote).
- T011 (diálogo) ‖ T012–T013 (bloques API).
- T016–T017 (engine) ‖ cualquier fase posterior a Phase 1.
- T018 (docs) ‖ T019.

## Implementation Strategy

1. **MVP**: Phase 1 + US1 (API) + US2 (lote) → ya se puede aplicar en lote vía API con vista previa.
2. US3 entrega la experiencia web completa (bloques + selección + diálogo) — es lo que el host usará.
3. US4 y Polish cierran.
4. Un solo PR (`019-actionable-suggestions`), squash-merge a `main`, CD a Railway; verificación T020 de solo lectura.
