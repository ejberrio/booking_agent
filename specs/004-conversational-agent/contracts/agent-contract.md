# Contrato — Agente, herramientas y endpoint

## Registro de herramientas (`app/agent/tools.py`)

Cada `ToolSpec` = (name, description, params schema, is_write, handler). El handler recibe `(session, channel, args, ctx)`.

| Herramienta | is_write | Mapea a (feature 003) |
|-------------|----------|------------------------|
| `get_calendar` | no | `pricing_app_service.get_calendar` |
| `get_history` | no | `pricing_app_service.history` |
| `propose_set_day` | sí | preview de `set_day_price` |
| `propose_set_range` | sí | `pricing_app_service.preview_range` |
| `propose_create_promotion` | sí | resumen de `promotion_service.create_promotion` |
| `propose_delete_promotion` | sí | resumen de `promotion_service.delete_promotion` |
| `propose_rollback` | sí | resumen de `rollback_and_publish` |
| `confirm_pending` | (control) | aplica el `AgentAction` proposed |
| `cancel_pending` | (control) | cancela el `AgentAction` proposed |

`confirm_pending`/`cancel_pending` solo se ofrecen al LLM cuando existe un `AgentAction` en estado proposed.

## Orquestador (`run_turn`)

```python
async def run_turn(session, channel, llm, *, conversation_id, user_text) -> AgentReply: ...
```
Comportamiento:
- **O1**: persiste el mensaje del host; arma el prompt con system + historial de la conversación (memoria).
- **O2**: llama al LLM con el conjunto de herramientas permitido (incluye confirm/cancel solo si hay proposed).
- **O3**: herramienta de **lectura** → ejecuta y realimenta al LLM (loop).
- **O4**: herramienta de **escritura** → crea `AgentAction(proposed)` con preview + fingerprint (+ `reinforced` si >14 días o >±25%); responde la propuesta y termina (no aplica).
- **O5**: `confirm_pending` → re-valida fingerprint: si cambió, crea nueva proposed (anterior `stale`) e informa; si no, aplica vía 003 con **origen=chat**, enlaza la auditoría al mensaje, marca `applied`.
- **O6**: `cancel_pending` o cambio de tema → marca `cancelled`.
- **O7**: sin `LLMConfig`/credenciales → respuesta clara, sin herramientas.
- **O8**: el modelo usado es `model_general` salvo en pasos de escritura/confirmación, que usan `model_actions`.

## Endpoint (`/chat`)

| Método | Ruta | Acción |
|--------|------|--------|
| POST | `/chat` | ejecuta un turno (no streaming) → `AgentReply` (útil para clientes simples/tests) |
| GET/POST | `/chat/stream` | **SSE**: emite eventos `token` (texto), `tool` (estado de herramienta) y `done` (resultado final) |

## Garantías de comportamiento

- **G1**: ninguna herramienta de escritura aplica sin un `confirm_pending` posterior (0% de escrituras sin confirmar).
- **G2**: una propuesta confirmada sobre estado cambiado → se re-propone, no se aplica (fingerprint).
- **G3**: toda aplicación queda auditada con **origen=chat** y enlazada al mensaje; es reversible.
- **G4**: respuestas de precio/disponibilidad provienen de herramientas (no inventadas).
- **G5**: sin LLM configurado → mensaje claro, sin intentar acciones.
- **G6**: las propuestas que superan el umbral se marcan `reinforced` y lo indican.

## Contrato de pruebas (FakeLLM guionizado + ChannelManager falso)

| Test | Verifica |
|------|----------|
| `test_query_uses_tool_not_invented` | consulta → llama `get_calendar`, responde con datos reales (G4) |
| `test_write_proposes_not_applies` | petición de cambio → `AgentAction(proposed)`, sin aplicar (G1) |
| `test_confirm_applies_origin_chat` | `confirm_pending` → aplica, audita origen=chat, enlaza mensaje (G3) |
| `test_confirm_stale_reproposes` | estado cambiado entre propuesta y confirmación → re-propone, no aplica (G2) |
| `test_cancel_marks_cancelled` | "no" → `cancelled`, sin aplicar |
| `test_reinforced_threshold` | cambio >14 días o >±25% → `reinforced=True` (G6) |
| `test_no_llm_config_message` | sin `LLMConfig` → mensaje claro, sin acciones (G5) |
