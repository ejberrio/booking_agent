# Data Model — Agente conversacional

Reutiliza `Conversation`, `Message`, `LLMConfig` (001) y la auditoría (`PriceChangeLog`/`PromotionChangeLog` con origen=chat). Añade **una** tabla para la acción propuesta; el resto son objetos de valor transitorios.

## Entidad nueva (persistida)

### AgentAction
Una acción de escritura propuesta por el agente, a la espera de confirmación.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| conversation_id | FK→Conversation | |
| message_id | FK→Message? | mensaje que originó la propuesta |
| tool | str | nombre de la herramienta de escritura (p. ej. `propose_set_range`) |
| arguments | JSONB | argumentos resueltos (unidad, fechas, precio, etc.) |
| preview | JSONB | resumen/diff (días afectados, antes/después) |
| fingerprint | str | huella del estado base (003) para detectar obsolescencia |
| reinforced | bool | True si supera el umbral (>14 días o >±25%) |
| status | enum(proposed, applied, cancelled, stale) | |
| applied_ref | str? | referencia a la auditoría resultante (p. ej. ids de PriceChangeLog) |

- Solo un `AgentAction` en estado `proposed` por conversación a la vez (la nueva propuesta cancela la anterior).
- Transiciones: proposed→applied | proposed→cancelled | proposed→stale (al confirmar con huella cambiada → se crea una nueva proposed).

## Objetos de valor (transitorios)

- **ToolSpec** (`app/agent/tools.py`): nombre, descripción, JSON schema de parámetros, `is_write` (bool), `handler` (callable). Define lo que el LLM puede llamar y alimenta los guardrails.
- **ToolCall / ToolResult**: par solicitado por el LLM y su resultado (para el loop y el historial).
- **AgentReply**: resultado de un turno → texto final, eventos (para SSE), `pending_action_id` (si quedó una propuesta), `applied` (bool).

## Reglas / invariantes (servicio)
1. Herramientas de lectura → se ejecutan; de escritura → crean `AgentAction(proposed)`, no aplican.
2. Confirmar re-valida `fingerprint` (003): si cambió → nueva `proposed` (status anterior `stale`); si no → aplica.
3. Aplicar usa los servicios de 003 con **origen=chat** y enlaza la auditoría al `message_id`.
4. Cancelar o cambiar de tema → `AgentAction.status=cancelled`.
5. Sin `LLMConfig` activa o sin credenciales → no se intentan acciones; respuesta clara.
6. El agente nunca produce precios/disponibilidad que no provengan de una herramienta de lectura.
