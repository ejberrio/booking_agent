# Feature Specification: Agente conversacional (backend)

**Feature Branch**: `004-conversational-agent`  
**Created**: 2026-06-26  
**Status**: Draft  
**Input**: Motor del chat agéntico (backend) con tool-calling que permite al host consultar y gestionar precios en lenguaje natural, usando como herramientas el motor de precios (003) y el conector (002), con LLM configurable (OpenAI por defecto). El agente propone y el host confirma; toda acción auditada (origen=chat) y reversible. Single-tenant, COP, solo Booking.

## Clarifications

### Session 2026-06-26

- Q: ¿Cómo se maneja la confirmación de una acción entre turnos? → A: Se **persiste la propuesta** (AgentAction: herramienta, argumentos, preview y huella del estado base). La confirmación aplica esa propuesta exacta; si el estado cambió, el agente re-propone.
- Q: ¿Qué dispara una confirmación reforzada (cambio masivo/sensible)? → A: Cuando el cambio afecta **más de 14 días** o mueve el precio **más de ±25%**.
- Q: ¿Qué protocolo de streaming usa el endpoint de chat? → A: **SSE (Server-Sent Events)**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar precios y disponibilidad en lenguaje natural (Priority: P1)

El host pregunta en lenguaje natural (p. ej. "¿cuánto cuesta el 15 de julio?", "¿qué disponibilidad tengo el primer fin de semana de agosto?") y el agente responde con datos reales (precio base, efectivo, disponibilidad, promociones), sin modificar nada.

**Why this priority**: Es el uso más frecuente y seguro (solo lectura); valida que el agente entiende fechas/intención y consulta los datos correctos.

**Independent Test**: Hacer preguntas de precio/disponibilidad por día y por rango y verificar que la respuesta coincide con los datos del modelo.

**Acceptance Scenarios**:

1. **Given** una unidad con precios cargados, **When** el host pregunta el precio de una fecha, **Then** el agente responde con el precio efectivo real de esa fecha.
2. **Given** un rango con promociones, **When** el host pregunta por ese rango, **Then** el agente resume precios efectivos y promociones vigentes.
3. **Given** una pregunta ambigua de fecha ("el próximo finde"), **When** el agente la interpreta, **Then** usa el rango correcto o pide aclaración si no puede resolverla.

---

### User Story 2 - Cambiar precios por chat con confirmación (Priority: P1)

El host pide un cambio (p. ej. "sube 20% los fines de semana de agosto"). El agente **propone** primero: muestra un resumen/preview (qué días, de qué valor a qué valor) y **espera un "sí" explícito**. Solo entonces aplica, audita (origen=chat) y publica. Nunca cambia precios sin confirmación.

**Why this priority**: Es el valor central (gestionar precios hablando) y el punto donde el principio III (human-in-the-loop) es crítico.

**Independent Test**: Pedir un cambio, verificar que el agente devuelve una propuesta sin aplicar; confirmar y verificar que se aplicó, quedó auditado (origen=chat) y publicado; responder "no" y verificar que no se aplicó nada.

**Acceptance Scenarios**:

1. **Given** una petición de cambio de precio, **When** el agente responde, **Then** entrega una propuesta (preview/diff + resumen) y NO aplica todavía.
2. **Given** una propuesta pendiente, **When** el host confirma ("sí"), **Then** el cambio se aplica, se audita (origen=chat) y se publica al canal.
3. **Given** una propuesta pendiente, **When** el host responde "no" o cambia de tema, **Then** no se aplica nada y la propuesta queda cancelada.
4. **Given** un cambio aplicado por chat, **When** se consulta la auditoría, **Then** figura con origen=chat y enlazado al mensaje que lo originó, y es reversible.

---

### User Story 3 - Gestionar promociones por chat (Priority: P2)

El host crea o elimina promociones por chat (p. ej. "crea una promo del 10% para la próxima semana"). El agente propone, confirma y aplica como en US2, reflejando el efecto en el precio efectivo.

**Why this priority**: Completa la gestión comercial conversacional; se apoya en el mismo flujo de confirmación.

**Independent Test**: Pedir crear una promo, confirmar, y verificar que la promo existe, baja el efectivo y queda auditada; pedir eliminarla y confirmar.

**Acceptance Scenarios**:

1. **Given** una petición de promoción, **When** el agente responde, **Then** propone (resumen) y aplica solo tras confirmación.
2. **Given** una promo creada por chat, **When** se consulta el calendario, **Then** el efectivo refleja el descuento.

---

### User Story 4 - Memoria y contexto de conversación (Priority: P2)

El agente recuerda, dentro de una conversación, la propiedad activa y las fechas en foco, y resuelve referencias relativas ("esos días", "súbelo otro 5%", "y para septiembre lo mismo").

**Why this priority**: Hace la conversación natural y reduce repetición; sin esto el host tendría que repetir el contexto cada turno.

**Independent Test**: En una conversación, fijar un rango en un turno y referirse a él en el siguiente ("súbelo 5% más"); verificar que el agente actúa sobre el mismo rango.

**Acceptance Scenarios**:

1. **Given** un rango mencionado en un turno, **When** el host dice "esos días", **Then** el agente usa el mismo rango.
2. **Given** una propiedad activa en contexto, **When** el host omite la propiedad, **Then** el agente asume la activa (o pide aclaración si hay varias y es ambiguo).

---

### User Story 5 - Configurar el LLM y usarlo según la tarea (Priority: P2)

El host configura el LLM (proveedor, modelo de conversación, modelo de acciones, parámetros, presupuesto). El agente usa el modelo apropiado: el económico para conversación/consulta y el más capaz para decidir acciones de escritura.

**Why this priority**: Control de costo/calidad y flexibilidad de proveedor (objetivo explícito del producto).

**Independent Test**: Cambiar el modelo en la configuración y verificar que el agente lo usa; verificar que las acciones de escritura usan el modelo de acciones.

**Acceptance Scenarios**:

1. **Given** una configuración de LLM, **When** el agente conversa, **Then** usa el modelo general configurado.
2. **Given** una acción de escritura, **When** el agente la decide/ejecuta, **Then** usa el modelo de acciones configurado.
3. **Given** un cambio de proveedor/modelo en la configuración, **When** el agente vuelve a actuar, **Then** usa el nuevo modelo sin cambios de código.

---

### User Story 6 - Persistencia del chat y trazabilidad (Priority: P3)

Las conversaciones y mensajes se guardan; cada acción (cambio de precio/promoción) queda enlazada al mensaje que la originó.

**Why this priority**: Continuidad y auditoría; no bloquea el uso básico.

**Independent Test**: Tener una conversación con una acción, recuperar el historial y comprobar que la acción está enlazada a su mensaje.

**Acceptance Scenarios**:

1. **Given** una conversación con un cambio aplicado, **When** se recupera el historial, **Then** los mensajes y la acción enlazada están presentes.

---

### Edge Cases

- **Confirmación ambigua**: si la respuesta no es un "sí" claro, el agente NO aplica y vuelve a preguntar.
- **Propuesta caducada**: si el estado cambió entre la propuesta y la confirmación, el agente re-propone (no aplica sobre datos viejos).
- **Petición fuera de límites**: si el precio pedido viola las reglas (min/max), el agente lo explica y no aplica.
- **Cambio masivo/sensible**: cambios que afectan más de 14 días o con variación de precio mayor a ±25% requieren confirmación reforzada.
- **Herramienta no permitida o fuera de alcance** (p. ej. eventos, otros canales): el agente lo indica en lugar de inventar.
- **Sin LLM configurado / sin saldo**: el agente responde con un mensaje claro (no falla en silencio) y no intenta acciones.
- **Error al publicar al canal**: el cambio local se conserva (auditado) y el agente informa la incidencia.
- **Alucinación de datos**: el agente debe basar precios/disponibilidad en las herramientas, nunca inventarlos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El agente MUST interpretar peticiones en lenguaje natural (incluidas fechas relativas) y decidir qué herramienta(s) invocar con qué argumentos (tool-calling).
- **FR-002**: El agente MUST responder consultas de precio/disponibilidad/promociones con datos obtenidos de las herramientas del motor de precios; NUNCA debe inventar valores.
- **FR-003**: Las herramientas disponibles MUST limitarse a un conjunto acotado mapeado a la feature 003 (consultar, fijar día, preview/aplicar rango, crear/eliminar promoción, rollback, historial); herramientas fuera de alcance se rechazan.
- **FR-004**: Para CUALQUIER acción de escritura, el agente MUST primero PROPONER (resumen + preview/diff) y aplicar SOLO tras una confirmación explícita del host. Sin confirmación, no se aplica nada.
- **FR-005**: El sistema MUST persistir la acción propuesta (pendiente) de modo que la confirmación en un turno posterior la aplique; una respuesta negativa o un cambio de tema la cancela.
- **FR-006**: Si el estado cambió entre la propuesta y la confirmación, el agente MUST re-proponer en lugar de aplicar sobre datos obsoletos.
- **FR-007**: Toda acción de escritura aplicada MUST quedar auditada con origen=chat, enlazada al mensaje que la originó, y MUST ser reversible (reutiliza la auditoría de 001/003).
- **FR-008**: El agente MUST usar la configuración de LLM: modelo general para conversación/consulta y modelo de acciones para decidir/ejecutar escrituras; el proveedor/modelo es configurable sin cambios de código.
- **FR-009**: El agente MUST mantener, dentro de una conversación, contexto de propiedad activa y fechas en foco, y resolver referencias relativas; si hay ambigüedad relevante, pide aclaración.
- **FR-010**: El agente MUST aplicar guardrails: **confirmación reforzada cuando el cambio afecta más de 14 días o mueve el precio más de ±25%**, y respeto a los límites de precio (no propone aplicar fuera de min/max).
- **FR-011**: El sistema MUST persistir conversaciones y mensajes y enlazar cada acción al mensaje originador.
- **FR-012**: El endpoint de chat MUST transmitir mediante **SSE (Server-Sent Events)** la respuesta del agente y el estado de las herramientas en ejecución.
- **FR-013**: Si no hay LLM configurado o no hay saldo/credenciales, el agente MUST responder con un mensaje claro y NO intentar acciones.
- **FR-014**: El alcance MUST limitarse a single-tenant, COP y canal Booking; las herramientas de eventos/mercado y otros canales quedan fuera (se añadirán detrás de la misma interfaz de herramientas).

### Key Entities *(include if feature involves data)*

Reutiliza `Conversation`, `Message`, `LLMConfig`, `PriceChangeLog`/`PromotionChangeLog` (features 001/003). Concepto propio:

- **Acción propuesta (AgentAction)**: una acción de escritura que el agente propuso y espera confirmación. Atributos: conversación, mensaje originador, herramienta, argumentos, resumen/preview (incl. huella del estado base), estado (propuesta, confirmada/aplicada, cancelada, caducada), enlace a la auditoría resultante.
- **Definición de herramienta (ToolSpec)**: descripción de cada herramienta disponible para el agente (nombre, propósito, parámetros, si es de lectura o de escritura) — usada para el tool-calling y los guardrails.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El agente nunca aplica una acción de escritura sin una confirmación explícita del host (0% de cambios sin confirmar).
- **SC-002**: Las respuestas de consulta coinciden con los datos del modelo (precio efectivo/disponibilidad) en el 100% de los casos verificados.
- **SC-003**: Toda acción aplicada por chat queda auditada con origen=chat, enlazada a su mensaje, y es reversible (100%).
- **SC-004**: Una propuesta aplicada sobre un estado cambiado se detecta y re-propone (0% de aplicaciones sobre datos obsoletos).
- **SC-005**: El agente usa el modelo configurado (general vs. acciones) y cambia de modelo/proveedor sin cambios de código.
- **SC-006**: El agente basa precios/disponibilidad en las herramientas; no inventa valores (verificado en pruebas con herramientas simuladas).
- **SC-007**: Sin LLM configurado, el agente responde con un mensaje claro y no intenta acciones (no falla en silencio).

## Assumptions

- **Reutiliza** el motor de precios (003) como herramientas, el conector (002) para publicar, y los modelos de LLM/conversación/mensaje y auditoría (001).
- **Confirmación persistida**: la acción propuesta se guarda (AgentAction) para que la confirmación en un turno posterior la aplique.
- **LLM**: OpenAI por defecto (modelo general económico para conversación, modelo de acciones más capaz para escrituras), detrás de una capa provider-agnostic.
- **Single-tenant, COP, solo Booking**; el "quién" de la auditoría se modela por origen (chat).
- **Streaming** vía el endpoint de chat; el frontend pulido es de otra feature (Fase 6) — aquí el alcance es el agente de backend y su endpoint.
- **Fuera de alcance**: herramientas de eventos/mercado y sugerencias (Fase 5), otros canales (Airbnb), y la UI/dashboard (Fase 6).
- **Pruebas** del agente con LLM y herramientas simuladas (sin llamar a la API real ni gastar tokens).
