---
description: "Task list — Modelo de datos del dominio"
---

# Tasks: Modelo de datos del dominio

**Input**: Design documents from `specs/001-data-model/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/data-access.md

**Tests**: INCLUIDOS. La constitución (principio IV) exige pruebas para el motor de precios y la auditoría; el contrato `contracts/data-access.md` define los tests requeridos.

**Organización**: por historia de usuario (US1–US5) para implementar y validar de forma incremental. Trabajo en `apps/api`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivo distinto, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1–US5)

---

## Phase 1: Setup (infraestructura compartida)

- [ ] T001 Crear paquetes `app/models/`, `app/domain/`, `app/services/` (con `__init__.py`) en `apps/api/app/`
- [ ] T002 [P] Añadir fixtures de prueba con Postgres async (sesión por test con rollback de transacción) en `apps/api/tests/conftest.py`
- [ ] T003 [P] Habilitar autogenerate de Alembic importando los modelos en `apps/api/migrations/env.py` (descomentar/añadir `from app.models import *`)

---

## Phase 2: Foundational (prerrequisitos bloqueantes)

**⚠️ Debe completarse antes de cualquier historia.**

- [ ] T004 [P] Definir enums compartidos (PropertyStatus, ChannelKind, ChangeOrigin, SuggestionStatus, PromotionType, BookingStatus, EventKind, Relevance) en `apps/api/app/models/enums.py`
- [ ] T005 [P] Añadir `TimestampMixin` (created_at/updated_at, timestamptz) en `apps/api/app/models/mixins.py`

**Checkpoint**: base lista — pueden comenzar las historias.

---

## Phase 3: User Story 1 - Propiedades, canales, unidades y precios por día (Priority: P1) 🎯 MVP

**Goal**: Representar propiedades (Medellín/COP), canales (Booking activo, channel-aware), tipos de unidad, calendario y precio base por unidad/día; consultar precio y disponibilidad.

**Independent Test**: Crear una propiedad con un tipo de unidad, fijar un precio para una fecha y consultar precio + disponibilidad de ese día.

### Tests for User Story 1

- [ ] T006 [P] [US1] Test: precio efectivo sin promociones == precio base, en `apps/api/tests/test_pricing.py`
- [ ] T007 [P] [US1] Test: disponibilidad compartida — un bloqueo/reserva reduce `units_available` de la unidad, en `apps/api/tests/test_models.py`

### Implementation for User Story 1

- [ ] T008 [P] [US1] Modelos `Property`, `Channel`, `UnitType` en `apps/api/app/models/property.py` (registrar en `app/models/__init__.py`)
- [ ] T009 [P] [US1] Modelos `CalendarDay` y `Rate` (precio base) en `apps/api/app/models/calendar.py` (constraint único por unidad+fecha)
- [ ] T010 [US1] Función pura `effective_price` (base + clamp; sin promos aún) y firmas en `apps/api/app/domain/pricing.py`
- [ ] T011 [US1] `PricingService.set_base_price` / `get_price` / `get_availability` en `apps/api/app/services/pricing_service.py` (depende de T008, T009, T010)
- [ ] T012 [US1] Migración Alembic inicial para property, channel, unit_type, calendar_day, rate en `apps/api/migrations/versions/` (`uv run alembic revision --autogenerate`)

**Checkpoint**: US1 funcional — se puede fijar y consultar precio/disponibilidad (MVP).

---

## Phase 4: User Story 2 - Auditar y revertir cambios de precio (Priority: P1)

**Goal**: Registrar cada cambio de precio (antes/después/origen) en una bitácora append-only y permitir rollback con detección de conflicto.

**Independent Test**: Cambiar un precio, ver la entrada de auditoría, revertirla y confirmar que vuelve al valor anterior; si hay cambios posteriores, exige confirmación.

### Tests for User Story 2

- [ ] T013 [P] [US2] Test: cada cambio de precio crea un `PriceChangeLog` con old/new/origin, en `apps/api/tests/test_audit.py`
- [ ] T014 [P] [US2] Test: rollback restaura el valor anterior como nuevo registro; conflicto requiere confirmación, en `apps/api/tests/test_audit.py`

### Implementation for User Story 2

- [ ] T015 [P] [US2] Modelo `PriceChangeLog` (append-only) en `apps/api/app/models/audit.py`
- [ ] T016 [US2] Extender `PricingService.set_base_price` para escribir `PriceChangeLog` con `origin` en `apps/api/app/services/pricing_service.py` (depende de T015)
- [ ] T017 [US2] `AuditService.rollback_change` con detección de conflicto (cambios posteriores en la misma unidad/fecha) en `apps/api/app/services/audit_service.py`
- [ ] T018 [US2] Migración Alembic para price_change_log en `apps/api/migrations/versions/`

**Checkpoint**: US1 + US2 funcionales — precios auditados y reversibles (principio III).

---

## Phase 5: User Story 3 - Promociones y reglas de precio (Priority: P2)

**Goal**: Promociones (porcentaje/monto, vigencia) que afectan el precio efectivo (gana la de mayor descuento, no se acumulan) y reglas de límite min/max.

**Independent Test**: Crear una promoción para un rango → el efectivo refleja el descuento; dos solapadas → gana la mayor; un precio fuera de min/max se señala.

### Tests for User Story 3

- [ ] T019 [P] [US3] Test: promociones solapadas → se aplica solo la de mayor descuento (no se acumulan), en `apps/api/tests/test_pricing.py`
- [ ] T020 [P] [US3] Test: precio por debajo del mínimo / sobre el máximo se señala inválido, en `apps/api/tests/test_pricing.py`

### Implementation for User Story 3

- [ ] T021 [P] [US3] Modelos `PricingRule` y `Promotion` en `apps/api/app/models/pricing.py`
- [ ] T022 [US3] `best_promotion` + integrar promos y clamp a la regla en `effective_price` en `apps/api/app/domain/pricing.py` (depende de T021)
- [ ] T023 [US3] Validación contra `PricingRule` (señalar fuera de rango) en `apps/api/app/services/pricing_service.py`
- [ ] T024 [US3] Migración Alembic para pricing_rule, promotion en `apps/api/migrations/versions/`

**Checkpoint**: precio efectivo completo (base + promos + límites).

---

## Phase 6: User Story 4 - Reservas, ocupación, eventos y sugerencias (Priority: P2)

**Goal**: Reservas que alimentan la ocupación; eventos deduplicados; sugerencias con estado y justificación, enlazadas al cambio aplicado.

**Independent Test**: Cargar reservas/eventos, generar una sugerencia y moverla proposed→approved→applied verificando el enlace al `PriceChangeLog`; registrar el mismo evento dos veces sin duplicar.

### Tests for User Story 4

- [ ] T025 [P] [US4] Test: `Event` con `dedup_key` es idempotente (sin duplicados), en `apps/api/tests/test_models.py`
- [ ] T026 [P] [US4] Test: sugerencia proposed→approved→applied crea/enlaza `PriceChangeLog`, en `apps/api/tests/test_suggestions.py`

### Implementation for User Story 4

- [ ] T027 [P] [US4] Modelo `Booking` + impacto en disponibilidad en `apps/api/app/models/booking.py`
- [ ] T028 [P] [US4] Modelos `Event` (con `dedup_key` único) y `PriceSuggestion` (máquina de estados) en `apps/api/app/models/market.py`
- [ ] T029 [US4] `SuggestionService.apply` (proposed→approved→applied; usa `PricingService` para el cambio auditado) en `apps/api/app/services/suggestion_service.py` (depende de T028, T016)
- [ ] T030 [P] [US4] `EventService.upsert` (deduplicación idempotente) en `apps/api/app/services/event_service.py` (depende de T028)
- [ ] T031 [US4] Migración Alembic para booking, event, price_suggestion en `apps/api/migrations/versions/`

**Checkpoint**: insumos de inteligencia (ocupación/eventos/sugerencias) disponibles.

---

## Phase 7: User Story 5 - Configuración de LLM e historial de chat (Priority: P3)

**Goal**: Persistir configuración del LLM y conversaciones/mensajes, enlazando acciones (cambios de precio) al mensaje que las originó.

**Independent Test**: Guardar una configuración de LLM y una conversación; un cambio de precio originado en un mensaje queda enlazado a ese mensaje y a su auditoría.

### Tests for User Story 5

- [ ] T032 [P] [US5] Test: un `PriceChangeLog` con `message_id` queda enlazado al `Message`, en `apps/api/tests/test_agent.py`

### Implementation for User Story 5

- [ ] T033 [P] [US5] Modelos `LLMConfig`, `Conversation`, `Message` en `apps/api/app/models/agent.py`
- [ ] T034 [US5] Asegurar relación `Message` ↔ `PriceChangeLog.message_id` en `apps/api/app/models/audit.py` (depende de T033)
- [ ] T035 [US5] Migración Alembic para llm_config, conversation, message en `apps/api/migrations/versions/`

**Checkpoint**: trazabilidad chat→acción→auditoría completa.

---

## Phase 8: Polish & Cross-Cutting

- [ ] T036 [P] Ejecutar la validación de `specs/001-data-model/quickstart.md` (flujo de 10 pasos) y dejar un script seed de ejemplo en `apps/api/scripts/seed_dev.py`
- [ ] T037 [P] Alinear `data-model.md` con el esquema final si hubo ajustes
- [ ] T038 `uv run ruff check .` y `uv run pytest -q` en verde (apps/api)

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)** bloquea todas las historias.
- **US1 (P1)** es el MVP y base de las demás (modelos de precio/calendario).
- **US2 (P1)** extiende el servicio de precios de US1 (auditoría/rollback).
- **US3 (P2)** completa el cálculo de precio efectivo (promos/reglas).
- **US4 (P2)** depende de US2 (sugerencia aplicada crea cambio auditado).
- **US5 (P3)** enlaza con la auditoría de US2.

### Dentro de cada historia
- Tests primero (deben fallar) → modelos → dominio → servicios → migración.

### Oportunidades de paralelismo
- Setup: T002, T003 en paralelo.
- Foundational: T004, T005 en paralelo.
- Por historia, los tests `[P]` y los modelos en archivos distintos `[P]` van en paralelo.

---

## Implementation Strategy

### MVP primero (US1)
1. Phase 1 (Setup) → 2. Phase 2 (Foundational) → 3. Phase 3 (US1) → **validar** (fijar/consultar precio + disponibilidad) → demo.

### Entrega incremental
US1 (MVP) → US2 (auditoría/rollback) → US3 (promos/reglas) → US4 (reservas/eventos/sugerencias) → US5 (LLM/chat). Cada historia añade valor sin romper las anteriores.

## Notes
- `[P]` = archivos distintos, sin dependencias pendientes.
- Cada modelo nuevo se registra en `app/models/__init__.py` (para autogenerate de Alembic).
- Commit por tarea o grupo lógico; ejecutar tests tras cada historia.
- El precio efectivo NO se persiste (se deriva en `app/domain/pricing.py`).
