# Research — Agente conversacional

Formato: Decisión / Justificación / Alternativas.

## 1. Tool-calling vía LiteLLM, LLM inyectable

- **Decisión**: El agente usa tool-calling en formato OpenAI a través de LiteLLM. El cliente LLM se **inyecta** en el orquestador (interfaz mínima `chat_with_tools`), de modo que los tests pasan un **FakeLLM** que devuelve respuestas/tool-calls guionizadas.
- **Justificación**: Provider-agnostic (principio II) y testeable sin gastar tokens (principio IV).
- **Alternativas**: SDK de OpenAI directo (acopla a un proveedor); framework de agentes pesado (LangChain) — innecesario para un conjunto acotado de herramientas.

## 2. Escrituras = proponer, no ejecutar (AgentAction persistida)

- **Decisión**: Las herramientas de **lectura** se ejecutan de inmediato en el loop. Las de **escritura** NO ejecutan: crean un `AgentAction` persistido (herramienta, argumentos, preview/resumen, **huella** del estado base, estado=proposed) y devuelven una propuesta. La confirmación es un paso explícito.
- **Justificación**: Human-in-the-loop (principio III); la propuesta sobrevive entre turnos (clarificación: persistir).
- **Alternativas**: ejecutar y permitir deshacer (rompe "el agente propone, el host confirma"); mantener la propuesta solo en memoria (se pierde entre turnos/instancias).

## 3. Confirmación como herramientas explícitas

- **Decisión**: Cuando existe un `AgentAction` en estado proposed para la conversación, el orquestador ofrece al LLM dos herramientas: `confirm_pending` y `cancel_pending`. Un "sí" del host → el LLM llama `confirm_pending`; "no"/cambio de tema → `cancel_pending` (o queda sin tocar). Al confirmar, se **re-valida la huella** (003): si el estado cambió, se re-propone; si no, se aplica.
- **Justificación**: Mantiene el control en el loop de herramientas (determinista y testeable con FakeLLM); la huella evita aplicar sobre datos obsoletos (clarificación).
- **Alternativas**: clasificar el "sí/no" con heurística de texto (frágil en lenguaje natural); auto-aplicar (viola principio III).

## 4. Enrutado de modelo (general vs. acciones)

- **Decisión**: Conversación/consulta usan `model_general`; las decisiones/ejecución de escritura usan `model_actions` (de `LLMConfig`). Por defecto OpenAI (gpt-4o-mini / gpt-4o).
- **Justificación**: Control costo/calidad (objetivo del producto); fiabilidad de tool-calling en escrituras.
- **Alternativas**: un solo modelo (más caro o menos fiable según el caso).

## 5. Memoria = historial de la conversación

- **Decisión**: El contexto (propiedad activa, fechas, "esos días") se logra pasando el historial de mensajes de la conversación al LLM; no hay tabla de contexto adicional.
- **Justificación**: Simplicidad (principio V); es el patrón estándar y suficiente a esta escala.
- **Alternativas**: store de contexto estructurado (más estado y migración; innecesario ahora).

## 6. Confirmación reforzada (umbral)

- **Decisión**: Al construir la propuesta, el orquestador marca `reinforced=True` si la acción afecta **>14 días** o la variación de precio supera **±25%** (clarificación). El resumen lo indica y exige confirmación explícita igualmente.
- **Justificación**: Red de seguridad para cambios grandes sin frenar los pequeños.
- **Alternativas**: umbrales más laxos/estrictos (evaluados en clarify).

## 7. Streaming SSE + núcleo no-streaming testeable

- **Decisión**: El endpoint expone **SSE** (eventos: token de texto, estado de herramienta, fin). La lógica vive en `run_turn()` **no-streaming** (devuelve el resultado completo) que los tests ejercitan; el endpoint SSE envuelve `run_turn`/streaming.
- **Justificación**: SSE encaja con FastAPI/web (clarificación); separar el núcleo permite tests deterministas.
- **Alternativas**: WebSocket (más complejo); solo respuesta completa (peor UX).

## 8. Seguridad: no inventar datos; sin LLM → mensaje claro

- **Decisión**: El system prompt obliga a basar precios/disponibilidad en herramientas (nunca inventar) y a proponer antes de escribir. Si no hay LLM configurado/saldo, el agente responde con un mensaje claro y no intenta acciones.
- **Justificación**: Confianza y robustez (SC-006, SC-007).
- **Alternativas**: dejar que el modelo responda de memoria (riesgo de alucinación).

## Sin NEEDS CLARIFICATION pendientes

Confirmación persistida, umbral (>14 días/±25%) y SSE se resolvieron en `/speckit-clarify`.
