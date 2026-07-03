# Tasks: Sugerencias de precio en el calendario + acción única "Aprobar y aplicar"

**Input**: Design documents from `/specs/014-calendar-suggestions/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/suggestions-api.md, quickstart.md

**Tests**: incluidos (Constitución IV: la lógica de aplicación de sugerencias publica precios — puede costar dinero). Patrón existente: pytest + SQLite async + dobles del Channel Manager; web se verifica con `npm run build`.

**Organization**: por user story; sin Setup ni migraciones (no cambia ningún modelo). US1 (backend) es el MVP; US2/US3/US4 son web.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1 (acción única), US2 (marcado calendario), US3 (resolver desde calendario), US4 (lista con botón único)

## Path Conventions

Monorepo: `apps/api/` (FastAPI) y `apps/web/` (Next.js), según plan.md.

---

## Phase 1: Foundational (sin tareas)

No hay prerequisitos bloqueantes: no hay modelos nuevos, migraciones ni configuración. Se salta directo a las user stories.

---

## Phase 2: User Story 1 — Resolver una sugerencia con una sola acción (P1) 🎯 MVP

**Goal**: `POST /suggestions/{id}/apply` = acción única segura: valida estado, recorta pasado, publica, audita; 409 honesto en conflicto; SyncIssue en fallo de canal. `reject` acepta `approved`. Ruta `approve` retirada.

**Independent Test**: con dobles, aplicar una sugerencia `proposed` produce `applied` + precios publicados + auditoría en una sola llamada; re-aplicar produce 409 sin llamadas al canal; `pytest -q` verde.

- [X] T001 [US1] Reforzar `apply_suggestion` en `apps/api/app/services/intelligence_service.py`: validar estado de entrada (`proposed`/`approved`; otro → `SuggestionStateError` con el estado real), recorte `effective_from = max(date_from, hoy)` (todo el rango pasado → error "vencida"), aplicar solo días restantes, devolver también `applied_from`; en fallo del canal registrar `SyncIssue` y relanzar sin marcar `applied` (sin commit no hay persistencia — verificar que `set_day_price` no comitea)
- [X] T002 [US1] Ampliar `reject` en `apps/api/app/services/suggestion_service.py` para aceptar `proposed` y `approved` (simetría R2); mensaje de error con el estado real cuando es terminal
- [X] T003 [US1] Actualizar `apps/api/app/api/routes/suggestions.py`: retirar la ruta `POST /{id}/approve`; en `apply` mapear errores — 404 solo inexistente, 409 conflicto de estado/vencida, 502 fallo de canal (commit de la SyncIssue antes de responder); en `reject` 409 en estado terminal; respuesta de `apply` incluye `applied_from`; el serializador añade `current_price` (precio base del primer día no pasado, `null` si no hay) y `GET /suggestions` acepta `pending=true` (= `proposed`+`approved`)
- [X] T004 [US1] Tests nuevos en `apps/api/tests/test_suggestion_resolve.py` (doble de canal reutilizando el patrón FakeCM): proposed→applied con publicación y `applied_change_id`; approved histórica→applied; applied/rejected→409 y CERO llamadas al canal; recorte parcial (`applied_from`=hoy, solo días restantes publicados); vencida total→409 sin efectos; canal caído→SyncIssue + sigue proposed; reject de approved→rejected; reject de applied→409; `current_price` en el listado y `pending=true` devuelve proposed+approved
- [X] T005 [US1] Ajustar tests existentes que usen la ruta `approve` o el comportamiento previo de `apply` (buscar en `apps/api/tests/` referencias a approve/apply de sugerencias) y correr `uv run pytest -q` completo en `apps/api/` (los 174 + nuevos en verde)

**Checkpoint**: backend completo y verde — la acción única funciona desde cualquier cliente.

---

## Phase 3: User Story 2 — Ver las sugerencias en el calendario (P1)

**Goal**: días con sugerencia vigente marcados (punto violeta + leyenda), conviviendo con promo/reserva/bloqueo; sin sugerencias, render idéntico al actual.

**Independent Test**: con una sugerencia `proposed` vigente, el calendario marca exactamente sus días; `npm run build` verde.

- [ ] T006 [P] [US2] Añadir prop opcional `suggestionDates?: Set<string>` a `apps/web/components/calendar/price-calendar.tsx`: punto violeta (`bg-violet-500`, title "Sugerencia") junto a los existentes y entrada "Sugerencia" en la leyenda solo si la prop llega con elementos
- [ ] T007 [US2] En `apps/web/app/(app)/calendar/page.tsx`: query `["suggestions"]` → `api.listSuggestions("proposed")`, helper de vigencia (`date_to >= hoy` en fecha local), computar `suggestionsByDate: Map<string, Suggestion[]>` y pasar `suggestionDates` al `PriceCalendar`

**Checkpoint**: contexto visual completo; clic aún abre solo el editor de rango.

---

## Phase 4: User Story 3 — Resolver la sugerencia desde el calendario (P2)

**Goal**: clic en día marcado → panel lateral con detalle completo (sugerido vs actual, rango, confianza %, racional) y acciones por sugerencia; refresco de calendario+lista; errores honestos del servidor.

**Independent Test**: clic en día marcado muestra el panel; "Aprobar y aplicar" actualiza precio y quita el marcador; reintento sobre resuelta muestra toast con el estado real y refresca.

- [ ] T008 [P] [US3] Crear `apps/web/components/calendar/suggestion-panel.tsx`: recibe `suggestions: Suggestion[]` del día seleccionado + `currentPrice: string | null`; por sugerencia muestra sugerido vs actual (formatCOP), rango completo, confianza %, `rationale.text`, botones "Aprobar y aplicar" (primario) y "Rechazar"; mutaciones `api.applySuggestion`/`api.rejectSuggestion` con toasts (éxito: "Sugerencia aplicada y publicada" / aviso de recorte si `applied_from` > `date_from`; error: `detail` del servidor) e invalidación de `["suggestions"]` y `["calendar"]` en `onSettled`
- [ ] T009 [US3] Integrar el panel en `apps/web/app/(app)/calendar/page.tsx`: cuando la selección es un solo día con sugerencias vigentes, renderizar `SuggestionPanel` en la columna lateral (encima de "Precio por canal"); tipos: `Suggestion` gana `applied_from?: string` en `apps/web/lib/types.ts` y el error de la API expone `detail` (ajustar `req()` en `apps/web/lib/api.ts` para incluir el detail del body en el mensaje del Error)

**Checkpoint**: ciclo completo ver→decidir→resolver sin salir del calendario.

---

## Phase 5: User Story 4 — La lista con el botón único (P2)

**Goal**: página de Sugerencias con exactamente dos acciones; dashboard intacto; `approveSuggestion` eliminado del cliente.

**Independent Test**: la lista muestra "Aprobar y aplicar"/"Rechazar", ambas funcionan; el build no referencia `approveSuggestion`.

- [ ] T010 [P] [US4] Actualizar `apps/web/components/suggestions/suggestion-card.tsx`: quitar botón/prop `onApprove`, renombrar botón principal a "Aprobar y aplicar", mostrar "Actual → Sugerido" con `current_price` (FR-004) y badge para `approved` históricas
- [ ] T011 [US4] Actualizar `apps/web/app/(app)/suggestions/page.tsx` (consultar pendientes `proposed`+`approved` vía `pending=true`, quitar mutación approve, pasar solo apply/reject, toast de recorte con `applied_from` como en T008) y en `apps/web/lib/api.ts` eliminar `approveSuggestion` y añadir `listPendingSuggestions`

**Checkpoint**: una sola semántica de resolución en toda la app.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T012 [P] Documentar en `docs/operations.md` (sección Sugerencias): acción única, recorte de días pasados, qué pasa en fallo de canal (SyncIssue), y que `approve` fue retirado
- [ ] T013 Verificación final: `cd apps/api && uv run pytest -q` y `cd apps/web && npm run build`; revisar `git diff` contra FR-012 (sin sugerencias vigentes, respuestas y render idénticos)
- [ ] T014 Verificación EN VIVO acotada según `quickstart.md` (crear sugerencia de prueba en fechas lejanas, resolverla desde el calendario, verificar auditoría y precio, REVERTIR con rollback) — requiere confirmación del host antes de escribir (Principio III)

---

## Dependencies & Execution Order

- **US1 (T001–T005)** primero: el backend seguro es prerequisito real de US3/US4 (la UI llamará al apply reforzado) aunque US2 no lo necesite.
- **US2 (T006–T007)** independiente de US1 (solo lectura) — puede ir en paralelo con US1; T006 ∥ T001–T005.
- **US3 (T008–T009)** depende de US1 (contrato de errores/`applied_from`) y US2 (marcado + selección).
- **US4 (T010–T011)** depende solo de US1; T010 ∥ T008.
- **Polish (T012–T014)** al final; T012 puede ir en cualquier momento tras US1.

```
US1 (backend) ──┬─▶ US3 (panel calendario) ─▶ Polish
US2 (marcado) ──┘
US1 ───────────▶ US4 (lista)
```

## Implementation Strategy

**MVP = US1**: con solo el backend reforzado, la acción única ya existe (la lista actual llama a `apply`, que ahora es seguro). Cada fase siguiente es un incremento demostrable. Entrega prevista: una sola rama/PR (patrón del proyecto), commits por fase.
