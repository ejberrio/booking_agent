# Implementation Plan: Agente conversacional (backend)

**Branch**: `004-conversational-agent` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/004-conversational-agent/spec.md`

## Summary

Agente de backend con loop de tool-calling: interpreta lenguaje natural, llama herramientas de **lectura** (consultar calendario/historial) de inmediato y, para **escrituras**, NO ejecuta — crea una **acción propuesta persistida** (`AgentAction`) con preview + huella y espera confirmación. Al confirmar, re-valida la huella (re-propone si cambió) y aplica vía el motor de precios (003), auditado con origen=chat y enlazado al mensaje. El LLM es configurable (LiteLLM; modelo general para conversar, modelo de acciones para escrituras). El endpoint de chat transmite por **SSE**. La memoria es el historial de la conversación (sin estado extra). Pruebas con LLM y Channel Manager **simulados** (sin gastar tokens ni tocar Beds24).

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI (SSE vía StreamingResponse), LiteLLM (tool-calling, multi-proveedor), SQLAlchemy async, Pydantic; reutiliza `pricing_app_service`/`promotion_service` (003), conector (002), modelos LLMConfig/Conversation/Message + auditoría (001)  
**Storage**: PostgreSQL 16 (reutiliza tablas; añade `agent_action`)  
**Testing**: pytest + pytest-asyncio; SQLite async; **FakeLLM** (respuestas/tool-calls guionizadas) + **ChannelManager falso**  
**Target Platform**: Servidor Linux (API en `apps/api`)  
**Project Type**: Web (backend del agente + endpoint)  
**Integration**: LLM vía LiteLLM (OpenAI por defecto: general gpt-4o-mini, acciones gpt-4o); herramientas mapeadas a la feature 003; publicación vía conector 002  
**Constraints**: human-in-the-loop (propuesta persistida + confirmación; reforzada si >14 días o >±25%); acciones auditadas origen=chat y reversibles; el agente nunca inventa datos (siempre vía herramientas); sin LLM configurado → mensaje claro, sin acciones  
**Scale/Scope**: 1 host, conversaciones cortas; volumen pequeño

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento |
|-----------|--------------|
| I. Spec-Driven | Procede de spec.md (004) con clarificaciones. ✅ |
| II. Provider-agnostic | LLM detrás de LiteLLM (modelo configurable); herramientas tras un registro; pricing/conector tras sus interfaces. ✅ |
| III. Human-in-the-loop | Escrituras solo tras confirmación; `AgentAction` persistida con huella anti-obsolescencia; auditado origen=chat y reversible. ✅ |
| IV. Tipado y pruebas | Orquestador y herramientas tipados; tests con FakeLLM/Channel falso (sin tokens reales). ✅ |
| V. Simplicidad | Memoria = historial (sin estado extra); solo 1 tabla nueva (`AgentAction`). ✅ |

**Resultado**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/004-conversational-agent/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── agent-contract.md     # registro de herramientas + orquestador + endpoint SSE + contratos de test
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/api/app/
├── agent/                      # NUEVO
│   ├── tools.py                # ToolSpec (nombre, schema, is_write, handler→servicios 003); registro
│   ├── orchestrator.py         # run_turn(): loop tool-calling; read inmediato; write→AgentAction; confirm/cancel
│   └── prompts.py              # system prompt (reglas: no inventar, proponer y confirmar)
├── llm/
│   └── client.py               # + chat_with_tools(messages, tools, model) vía LiteLLM; Protocol LLM (inyectable)
├── models/
│   └── agent.py                # + AgentAction (junto a LLMConfig/Conversation/Message)
└── api/routes/
    └── chat.py                 # upgrade: POST /chat (turno) + GET /chat/stream (SSE de tokens + estado de tools)

apps/api/migrations/versions/   # NUEVA migración: agent_action

apps/api/tests/
└── test_agent_orchestrator.py  # FakeLLM guionizado: consulta de lectura; propuesta de escritura (no aplica);
                                #   confirmación aplica + audita origen=chat; huella obsoleta re-propone; "no" cancela;
                                #   sin LLM configurado → mensaje claro
```

**Structure Decision**: Nuevo paquete `app/agent/` (orquestador + registro de herramientas + prompts), ampliación de `app/llm/client.py` (tool-calling inyectable), 1 modelo nuevo (`AgentAction`) y el endpoint SSE en `chat.py`. La **memoria** se logra pasando el historial de mensajes al LLM (sin tabla de contexto). Las escrituras reutilizan `pricing_app_service`/`promotion_service` (003); la publicación, el conector (002).

## Complexity Tracking

> Sin violaciones de la constitución. No aplica.
