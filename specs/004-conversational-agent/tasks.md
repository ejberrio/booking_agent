---
description: "Task list — Agente conversacional (backend)"
---

# Tasks: Agente conversacional (backend)

**Input**: Design documents from `specs/004-conversational-agent/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/agent-contract.md

**Tests**: INCLUIDOS (constitución IV). Con **FakeLLM** (tool-calls guionizados) + **ChannelManager falso** — sin tokens reales ni API de Beds24.

**Organización**: por historia de usuario (US1–US6). Trabajo en `apps/api`. Reutiliza tools de 003, conector 002, modelos LLM/chat/auditoría de 001.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: archivo distinto, sin dependencias pendientes.
- **[Story]**: US1–US6.

---

## Phase 1: Setup

- [ ] T001 [P] Crear paquete `app/agent/` (con `__init__.py`) en `apps/api/app/`

---

## Phase 2: Foundational (LLM tool-calling, herramientas de lectura, AgentAction)

**⚠️ Bloqueante para todas las historias.**

- [ ] T002 Capa de tool-calling: `chat_with_tools(messages, tools, model)` vía LiteLLM + `Protocol` LLM inyectable (para FakeLLM) en `apps/api/app/llm/client.py`
- [ ] T003 [P] Modelo `AgentAction` + enum `AgentActionStatus` en `apps/api/app/models/agent.py` y `apps/api/app/models/enums.py` (registrar en `app/models/__init__.py`)
- [ ] T004 [P] System prompt (no inventar datos; proponer y confirmar) en `apps/api/app/agent/prompts.py`
- [ ] T005 Registro de herramientas (`ToolSpec`) + herramientas de **lectura** (`get_calendar`, `get_history`) mapeadas a la feature 003, en `apps/api/app/agent/tools.py`
- [ ] T006 Migración Alembic para `agent_action` en `apps/api/migrations/versions/`

**Checkpoint**: base del agente lista (LLM, tools de lectura, AgentAction).

---

## Phase 3: User Story 1 - Consultar en lenguaje natural (Priority: P1) 🎯 MVP

**Goal**: Responder consultas de precio/disponibilidad con datos reales (vía herramientas), sin inventar.

**Independent Test**: Preguntar el precio de una fecha → el agente llama `get_calendar` y responde el valor real; sin LLM configurado → mensaje claro.

### Tests for User Story 1

- [ ] T007 [P] [US1] Test: consulta → llama `get_calendar` y responde datos reales (no inventa); sin `LLMConfig` → mensaje claro sin acciones, en `apps/api/tests/test_agent_orchestrator.py`

### Implementation for User Story 1

- [ ] T008 [US1] Orquestador base `run_turn` (persiste mensaje, arma prompt + historial, loop de tool-calling con herramientas de lectura; sin `LLMConfig` → mensaje claro) en `apps/api/app/agent/orchestrator.py`
- [ ] T009 [US1] Endpoint `POST /chat` (no streaming) → `AgentReply`, en `apps/api/app/api/routes/chat.py`

**Checkpoint**: consultas por chat funcionando (MVP).

---

## Phase 4: User Story 2 - Cambiar precios con confirmación (Priority: P1)

**Goal**: Petición de cambio → propuesta persistida (no aplica); confirmar aplica (origen=chat, enlazado, reversible); huella obsoleta re-propone; "no" cancela.

**Independent Test**: Pedir un cambio → `AgentAction(proposed)` sin aplicar; confirmar → aplicado y auditado origen=chat; cambiar el estado y confirmar → re-propone; "no" → cancelado.

### Tests for User Story 2

- [ ] T010 [P] [US2] Tests: escritura propone (proposed, no aplica); `confirm_pending` aplica + audita origen=chat + enlaza mensaje; huella obsoleta → re-propone; `cancel`/"no" → cancelled, en `apps/api/tests/test_agent_orchestrator.py`

### Implementation for User Story 2

- [ ] T011 [US2] Herramientas de **escritura** (`propose_set_day`, `propose_set_range`) + `confirm_pending`/`cancel_pending` (ofrecidas solo si hay proposed) en `apps/api/app/agent/tools.py`
- [ ] T012 [US2] Orquestador: write → `AgentAction(proposed)` con preview + fingerprint; `confirm_pending` → re-valida fingerprint (re-propone si cambió) y aplica vía 003 con origen=chat enlazado; `cancel_pending` → cancelled, en `apps/api/app/agent/orchestrator.py`
- [ ] T013 [US2] Guardrail de umbral: marcar `reinforced` si >14 días o variación >±25%, en `apps/api/app/agent/orchestrator.py`

**Checkpoint**: cambios de precio por chat, seguros (propose→confirm) y auditados.

---

## Phase 5: User Story 3 - Promociones por chat (Priority: P2)

**Goal**: Crear/eliminar promociones por chat con el mismo flujo de confirmación.

**Independent Test**: "crea una promo del 10% la próxima semana" → propone → confirmar → la promo existe, baja el efectivo y queda auditada.

### Tests for User Story 3

- [ ] T014 [P] [US3] Test: crear promo por chat propone→confirma→crea + re-publica + auditada, en `apps/api/tests/test_agent_orchestrator.py`

### Implementation for User Story 3

- [ ] T015 [US3] Herramientas `propose_create_promotion`/`propose_delete_promotion` y su aplicación al confirmar (vía `promotion_service`), en `apps/api/app/agent/tools.py` (+ wiring en `orchestrator.py`)

**Checkpoint**: gestión de promociones conversacional.

---

## Phase 6: User Story 4 - Memoria y contexto (Priority: P2)

**Goal**: Resolver referencias relativas usando el historial (propiedad/fechas en foco).

**Independent Test**: Fijar un rango en un turno y decir "súbelo 5% más" → actúa sobre el mismo rango.

### Tests for User Story 4

- [ ] T016 [P] [US4] Test: referencia relativa ("esos días") usa el rango previo del historial, en `apps/api/tests/test_agent_orchestrator.py`

### Implementation for User Story 4

- [ ] T017 [US4] Incluir el historial de la conversación en el prompt (memoria) y soporte de referencias relativas, en `apps/api/app/agent/orchestrator.py`

**Checkpoint**: conversación natural con contexto.

---

## Phase 7: User Story 5 - LLM configurable y enrutado de modelo (Priority: P2)

**Goal**: Usar `model_general` para conversar y `model_actions` para escrituras; cambiar de modelo por configuración.

**Independent Test**: Cambiar el modelo en `LLMConfig` y verificar que el agente lo usa; las escrituras usan el modelo de acciones.

### Tests for User Story 5

- [ ] T018 [P] [US5] Test: conversación usa `model_general`; escritura/confirmación usa `model_actions`; cambia con `LLMConfig`, en `apps/api/tests/test_agent_orchestrator.py`

### Implementation for User Story 5

- [ ] T019 [US5] Enrutado de modelo (general vs. actions) leyendo `LLMConfig`, en `apps/api/app/agent/orchestrator.py`

**Checkpoint**: control costo/calidad y flexibilidad de proveedor.

---

## Phase 8: User Story 6 - Persistencia y streaming (Priority: P3)

**Goal**: Guardar mensajes y enlazar acciones a su mensaje; exponer streaming SSE.

**Independent Test**: Conversación con una acción → historial recuperable con la acción enlazada; `/chat/stream` emite eventos.

### Tests for User Story 6

- [ ] T020 [P] [US6] Test: conversación con acción → historial recuperable y acción enlazada al mensaje, en `apps/api/tests/test_agent_orchestrator.py`

### Implementation for User Story 6

- [ ] T021 [US6] Persistir mensajes (asistente/herramienta) y enlazar acción↔mensaje, en `apps/api/app/agent/orchestrator.py`
- [ ] T022 [US6] Endpoint `GET /chat/stream` (SSE: eventos `token`/`tool`/`done`) envolviendo `run_turn`, en `apps/api/app/api/routes/chat.py`

**Checkpoint**: trazabilidad completa + streaming.

---

## Phase 9: Polish & Cross-Cutting

- [ ] T023 [P] Documentar los endpoints `/chat` y `/chat/stream` en `apps/api/README.md`
- [ ] T024 `uv run ruff check .` y `uv run pytest -q` en verde (apps/api)

---

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2: LLM tool-calling + tools de lectura + AgentAction)** bloquea las historias.
- **US1 (P1, MVP)**: consultar (loop de lectura).
- **US2 (P1)**: escrituras propose→confirm (núcleo de seguridad).
- **US3 (P2)**: promociones (sobre el flujo de US2).
- **US4 (P2)**: memoria (historial en el prompt).
- **US5 (P2)**: enrutado de modelo.
- **US6 (P3)**: persistencia + SSE.

### Dentro de cada historia
- Test primero (FakeLLM) → herramientas → orquestador → endpoint.

### Paralelismo
- Foundational: T003, T004 en paralelo (archivos distintos). Los tests `[P]` son el primer task de cada historia. `orchestrator.py`, `tools.py`, `chat.py` y el archivo de test son secuenciales entre sí (mismo archivo).

---

## Implementation Strategy

### MVP primero (US1)
Setup → Foundational → US1 (consultar por chat) → validar (FakeLLM) → demo.

### Entrega incremental
US1 (consultar) → US2 (cambiar con confirmación) → US3 (promos) → US4 (memoria) → US5 (modelo) → US6 (persistencia + SSE). Cada historia añade valor sin romper las anteriores.

## Notes
- `[P]` = archivos distintos, sin dependencias pendientes.
- LLM **inyectable** → tests con `FakeLLM` (tool-calls guionizados), sin tokens reales; ChannelManager falso para publicar.
- Escrituras: el agente PROPONE (AgentAction) y aplica solo tras `confirm_pending`; auditado origen=chat y reversible.
- Reutiliza `pricing_app_service`/`promotion_service` (003) y el conector (002); nada de lógica duplicada.
