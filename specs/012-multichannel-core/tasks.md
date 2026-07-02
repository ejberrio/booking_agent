# Tasks: Núcleo multi-canal (Booking.com + Airbnb)

**Input**: Design documents from `/specs/012-multichannel-core/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos (Principio IV de la constitución: adaptadores y límites no se mergean sin pruebas; SC-006 exige cobertura de las rutas nuevas). Patrón del repo: dobles del Channel Manager, sin APIs reales.

**Organization**: tareas agrupadas por user story para permitir implementación y prueba independientes.

**Fuera de alcance (issue #91)**: la sincronización de CAMBIOS DE ESTADO de reservas en
re-import (p. ej. cancelaciones remotas) es un gap pre-existente y NO se corrige aquí —
esta feature solo corrige `channel_kind`. No tocar la lógica de `status` en T010.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede correr en paralelo (archivos distintos, sin dependencia pendiente)
- **[Story]**: US1 (canal real en reservas), US2 (agente multi-canal), US3 (estado/dashboard)

## Path Conventions

Monorepo: `apps/api` (FastAPI) y `apps/web` (Next.js). Rutas relativas a la raíz del repo.

---

## Phase 1: Setup

**Purpose**: preparación mínima — no hay proyecto nuevo ni dependencias nuevas.

- [X] T001 Añadir setting `channels_active: str = "booking,airbnb"` (CSV → helper `active_channel_kinds() -> list[ChannelKind]` tolerante a espacios/valores inválidos) en apps/api/app/core/config.py y documentar la variable en .env.example si existe

**Checkpoint**: settings disponible para dominio y agente.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el canal de origen debe fluir por el puerto antes de cualquier historia.

- [X] T002 Extender DTO `RemoteBooking` con `channel: str | None = None` (token neutro en minúsculas; docstring con semántica y regla None=no reportado) en apps/api/app/channels/base.py según contracts/channel-manager-port.md
- [X] T003 [P] Mapear canal en `Beds24V2Adapter.get_bookings`: `b.get("channel")` con fallback a inferencia por `referer` ("booking"→booking, "airbnb"→airbnb, si no → None), normalizado a minúsculas, sin lanzar excepciones por este campo, en apps/api/app/channels/beds24_v2.py
- [X] T004 [P] Mapear canal best-effort desde `referer` en `Beds24Adapter.get_bookings` (V1 legacy de lectura, misma regla de inferencia) en apps/api/app/channels/beds24.py
- [X] T005 [P] Test de adaptadores: V2 mapea `channel`/`referer`/ausente → token correcto o None (payloads dobles, incluye origen desconocido) en apps/api/tests/test_beds24_v2_channels.py

**Checkpoint**: el puerto entrega el canal de origen — las user stories pueden arrancar.

---

## Phase 3: User Story 1 — Reservas con su canal real de origen (Priority: P1) 🎯 MVP

**Goal**: cada reserva importada registra Booking/Airbnb/directo según el canal manager; re-importar corrige históricos sin duplicar.

**Independent Test**: import simulado con orígenes mixtos (booking/airbnb/None) → `channel_kind` correcto; re-import con reserva pre-existente mal etiquetada → corregida, 0 duplicados.

### Tests for User Story 1

- [X] T006 [P] [US1] Tests de import multi-canal (doble del adapter con reservas booking/airbnb/origen None → booking/airbnb/direct; lote NUNCA aborta por origen desconocido) en apps/api/tests/test_sync_channels.py
- [X] T007 [P] [US1] Tests de corrección en re-import (sembrar Booking existente con channel_kind=booking cuyo remoto reporta airbnb → re-import lo corrige y cuenta en updated_count; sin duplicados por external_ref; una reserva cancelada conserva su canal) en apps/api/tests/test_sync_channels.py
- [X] T008 [P] [US1] Tests de upsert de canales desde config (CHANNELS_ACTIVE=booking,airbnb → dos filas Channel activas; quitar airbnb de la config → fila queda is_active=False y sus reservas intactas) en apps/api/tests/test_sync_channels.py

### Implementation for User Story 1

- [X] T009 [US1] Implementar `_map_channel(token: str | None) -> ChannelKind` (booking*→booking, airbnb*→airbnb, resto/None→direct) en apps/api/app/services/sync_service.py
- [X] T010 [US1] Usar el canal real en el import de reservas: crear con `channel_kind=_map_channel(rb.channel)`; si la reserva existe y difiere su channel_kind, actualizarla y contarla en `updated_count` en apps/api/app/services/sync_service.py (reemplaza el hardcode `ChannelKind.booking` de la rama de creación)
- [X] T011 [US1] Reescribir `_upsert_property` para upsert de canales desde `settings.active_channel_kinds()`: crear/activar los configurados, desactivar los registrados no configurados (reemplaza el hardcode de `Channel(kind=ChannelKind.booking)`) en apps/api/app/services/sync_service.py
- [X] T012 [US1] Verificar suite completa verde (las 109 existentes + nuevas) con `cd apps/api && uv run pytest -q`

**Checkpoint**: US1 completa y demostrable por sí sola (MVP: datos correctos).

---

## Phase 4: User Story 2 — Preguntar al agente por canal (Priority: P2)

**Goal**: el agente conoce los canales activos, filtra reservas por canal y avisa que los cambios publican a todos los canales.

**Independent Test**: con reservas mixtas sembradas, `get_bookings(channel="airbnb")` devuelve solo esas; `system_prompt(active_channels=[...])` menciona ambos canales y la publicación multi-canal.

### Tests for User Story 2

- [X] T013 [P] [US2] Tests de la tool `get_bookings`: filtro `channel="airbnb"` → solo esas reservas; sin filtro → todas con campo `channel`; canal inválido rechazado por schema, en apps/api/tests/test_agent_bookings.py
- [X] T014 [P] [US2] Tests del prompt: `system_prompt(active_channels=["booking","airbnb"])` contiene "Booking.com y Airbnb" y la regla de publicación a todos los canales; `system_prompt()` sin args sigue funcionando (retro-compatibilidad), en apps/api/tests/test_agent_prompts.py

### Implementation for User Story 2

- [X] T015 [US2] Parametrizar `system_prompt(today=None, active_channels=None)` según contracts/agent-tools.md (presentación multi-canal, regla FR-006 de publicación a todos los canales, instrucción de identificar canal en respuestas de reservas; conservar TODAS las reglas existentes) en apps/api/app/agent/prompts.py
- [X] T016 [US2] Inyectar canales activos en el orquestador: consultar `Channel.is_active` de la BD y pasar `active_channels` a `system_prompt` (patrón de `_units_context`) en apps/api/app/agent/orchestrator.py
- [X] T017 [US2] Extender tool `get_bookings`: parámetro opcional `channel` (enum booking|airbnb|direct) en el ToolSpec, filtro SQL por `Booking.channel_kind` y campo `channel` en cada fila de salida, en apps/api/app/agent/tools.py
- [X] T018 [US2] Ajustar aserciones de prompt existentes que esperan el texto viejo ("solo el canal Booking") en apps/api/tests/test_agent_orchestrator.py y cualquier otro test afectado; suite completa verde

**Checkpoint**: US2 completa — el chat distingue canales.

---

## Phase 5: User Story 3 — Estado y dashboard por canal (Priority: P3)

**Goal**: `/status` y el dashboard muestran canales conectados y reservas por canal; textos multi-canal.

**Independent Test**: con reservas mixtas, `GET /status` incluye el bloque `channels` con conteos; el dashboard renderiza la tarjeta "Canales"; ningún texto dice "solo Booking.com".

### Tests for User Story 3

- [X] T019 [P] [US3] Tests de `/status`: bloque `channels` con conteos por canal (orden booking, airbnb, direct); resiliencia (si el cálculo falla → `channels: []`, respuesta 200) en apps/api/tests/test_status.py (extender el existente)

### Implementation for User Story 3

- [X] T020 [US3] Añadir `_channels_status()` (filas Channel + conteo de Booking confirmadas por channel_kind, try/except + timeout, patrón del endpoint) y campo `channels` en la respuesta de `GET /status`; bump VERSION, en apps/api/app/api/routes/status.py según contracts/status-api.md
- [X] T021 [US3] Actualizar description de la app a multi-canal ("Booking.com y Airbnb vía Channel Manager") en apps/api/app/main.py
- [X] T022 [P] [US3] Tipos `ChannelStatus`/`SystemStatus` en apps/web/lib/types.ts y método `api.getStatus()` (proxy `/status`) en apps/web/lib/api.ts
- [X] T023 [US3] Tarjeta "Canales" en el dashboard (canales activos con conteo de reservas por canal; estados de carga/fallo suaves) en apps/web/app/(app)/page.tsx
- [X] T024 [P] [US3] Metadata multi-canal en apps/web/app/layout.tsx (description) y revisión de textos "solo Booking" visibles en la web (grep "Booking.com" en apps/web/app y ajustar los que afirmen exclusividad)
- [X] T025 [US3] `cd apps/web && npm run build` verde

**Checkpoint**: US3 completa — visibilidad multi-canal end-to-end.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T026 [P] Documentar en docs/operations.md: sección "Multi-canal" (qué significa CHANNELS_ACTIVE, cómo corregir históricos re-importando, cómo leer /status.channels)
- [X] T027 [P] Actualizar specs/012-multichannel-core/quickstart.md si la implementación divergió; marcar checklist de requirements si aplica
- [X] T028 Ejecutar quickstart local completo: `uv run pytest -q` (api) + `npm run build` (web) + revisión manual de textos; preparar PR

---

## Dependencies & Execution Order

- **Setup (T001)** → **Foundational (T002–T005)** → historias.
- **US1 (T006–T012)**: solo depende de Foundational. 🎯 MVP.
- **US2 (T013–T018)**: depende de Foundational; usa datos de US1 para probar filtros (los tests siembran los suyos ⇒ puede desarrollarse en paralelo con US1 tras T002, pero se recomienda tras US1 para validar E2E).
- **US3 (T019–T025)**: depende de US1 (conteos correctos); independiente de US2.
- **Polish (T026–T028)**: al final.

```text
T001 → T002 → {T003, T004, T005}
             → US1: {T006,T007,T008} → T009 → T010 → T011 → T012
             → US2: {T013,T014} → T015 → T016 → T017 → T018   (tras Foundational)
             → US3: T019 → T020 → T021 · {T022} → T023 → {T024} → T025   (tras US1)
→ {T026, T027} → T028
```

### Parallel opportunities

- T003 ∥ T004 ∥ T005 (archivos distintos).
- Dentro de US1: T006 ∥ T007 ∥ T008 (mismo archivo nuevo — escribirlos juntos o secuencial; paralelizables con los de US2 T013/T014).
- US2 y US3 pueden avanzar en paralelo tras US1 (backend tools/prompt vs status/web).
- T022 ∥ T024 (web, archivos distintos).

## Implementation Strategy

1. **MVP primero**: Setup + Foundational + US1 → datos correctos (el valor central). Parar aquí ya sería desplegable.
2. **Incremento 2**: US2 (agente) — la interfaz principal deja de mentir.
3. **Incremento 3**: US3 (status/dashboard/textos) — visibilidad.
4. Polish + PR único a `main` (patrón del repo: squash con CI verde).
