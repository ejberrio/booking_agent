# Feature Specification: Chat flotante accesible desde cualquier pantalla

**Feature Branch**: `024-floating-chat`
**Created**: 2026-10-09
**Status**: Draft
**Input**: User description: "Chat flotante accesible desde cualquier pantalla (issue #127)."

## Contexto

Hoy el asistente solo está en la sección **Chat**. La conversación vive en la pantalla: si el host cambia de sección o recarga, la pierde de vista aunque el servidor la guarda. El host quiere un **botón flotante** (abajo a la derecha) que abra el asistente en un **panel lateral** desde cualquier pantalla, sin salir de lo que está haciendo, con la **misma conversación** que la sección Chat.

Decisiones por defecto (convencionales, sin pregunta al host):
1. El panel se superpone a la derecha sin oscurecer la página (el host sigue viendo el calendario o la lista); en celular ocupa la pantalla completa.
2. Atajo de teclado: **Ctrl+K / ⌘K** abre y cierra el panel; **Esc** lo cierra.
3. El ancho del panel se puede arrastrar (360–720 px) y se recuerda en el navegador.
4. En la propia sección Chat el botón flotante no aparece (ya está el chat en pantalla).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Abrir el asistente desde cualquier pantalla (Priority: P1)

Como host, desde el calendario (o cualquier otra sección) quiero abrir el asistente con un botón flotante, pedirle algo ("¿cuánto cobro el 14 de noviembre?", "baja el 20 a 250.000") y seguir viendo la pantalla en la que estaba.

**Why this priority**: es el pedido central.

**Independent Test**: en el Calendario pulsar el botón flotante → se abre el panel a la derecha con el calendario visible; escribir una pregunta → responde con las mismas herramientas que el Chat; una propuesta de cambio muestra Confirmar/Cancelar y al confirmar se aplica.

**Acceptance Scenarios**:

1. **Given** cualquier pantalla autenticada excepto Chat, **When** el host mira la esquina inferior derecha, **Then** ve el botón del asistente; en la pantalla de acceso no aparece.
2. **Given** el panel abierto, **When** el host escribe, **Then** obtiene las mismas capacidades que en Chat (herramientas, estado "consultando…", propuestas con Confirmar/Cancelar).
3. **Given** el panel abierto, **When** el host pulsa Esc, la X o el botón flotante, **Then** el panel se cierra y la página sigue igual.
4. **Given** el host pulsa Ctrl+K (⌘K en Mac), **When** el panel está cerrado/abierto, **Then** se abre/cierra.
5. **Given** un celular, **When** abre el asistente, **Then** ocupa la pantalla completa con un botón para cerrar.
6. **Given** que el asistente aplica un cambio (precio, disponibilidad), **When** termina, **Then** la pantalla de fondo refleja el cambio sin recargar.

---

### User Story 2 - Misma conversación en el panel y en la sección Chat (Priority: P1)

Como host quiero que lo que escribo en el panel aparezca en la sección Chat y viceversa, y que la conversación siga ahí al cambiar de sección o recargar.

**Why this priority**: sin continuidad, el panel sería un segundo chat desconectado.

**Independent Test**: preguntar algo en el panel, ir a Chat → la conversación está; recargar la página → sigue; una propuesta pendiente sigue con Confirmar/Cancelar.

**Acceptance Scenarios**:

1. **Given** una conversación en el panel, **When** el host abre la sección Chat, **Then** ve los mismos mensajes.
2. **Given** una conversación en curso, **When** el host recarga o vuelve otro día, **Then** se muestra la última conversación con sus mensajes.
3. **Given** una propuesta pendiente de confirmar, **When** el host recarga, **Then** sigue viendo Confirmar/Cancelar.
4. **Given** el host pulsa "Nueva conversación", **When** escribe, **Then** empieza una conversación nueva y la anterior queda en el historial.

---

### User Story 3 - Historial de conversaciones recientes (Priority: P2)

Como host quiero ver mis conversaciones recientes (título y fecha) y retomar cualquiera.

**Independent Test**: con 3 conversaciones, abrir "Recientes" → aparecen con el primer mensaje como título; elegir una → se cargan sus mensajes y se puede seguir.

**Acceptance Scenarios**:

1. **Given** conversaciones previas, **When** el host abre "Recientes", **Then** ve hasta 20, la más reciente primero, con título (primer mensaje del host, recortado) y fecha.
2. **Given** una conversación elegida, **When** el host escribe, **Then** el asistente continúa esa conversación.

### Edge Cases

- Conversación guardada que ya no existe (borrada) → se empieza una nueva sin error.
- El host envía desde el panel mientras la sección Chat está abierta en otra pestaña → la otra pestaña muestra los mensajes al volver a enfocarse (recarga del historial).
- Respuestas fijas del servidor se muestran traducidas al idioma activo (feature 021); el texto libre del asistente queda como vino.
- Mensajes internos (sistema/herramientas) nunca se muestran.
- Panel abierto y navegación entre secciones → el panel sigue abierto con la misma conversación.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Las pantallas autenticadas (salvo Chat) MUST mostrar un botón flotante que abre/cierra el panel del asistente; la pantalla de acceso no.
- **FR-002**: El panel MUST ofrecer las mismas capacidades que la sección Chat (mismo endpoint, herramientas, propuestas con confirmación, idioma).
- **FR-003**: El panel MUST cerrarse con Esc, con su botón de cerrar y con el botón flotante; Ctrl+K / ⌘K MUST alternarlo.
- **FR-004**: En pantallas anchas el panel MUST superponerse a la derecha sin bloquear la página y su ancho MUST poder ajustarse (360–720 px, recordado en el navegador); en pantallas estrechas MUST ocupar la pantalla completa.
- **FR-005**: El panel y la sección Chat MUST compartir la conversación en curso (mismos mensajes, propuesta pendiente y estado).
- **FR-006**: La conversación en curso MUST recuperarse al recargar o al volver (identificador recordado en el navegador + mensajes desde el servidor), incluida una propuesta pendiente.
- **FR-007**: El sistema MUST listar las conversaciones recientes (máx. 20, más reciente primero) con título (primer mensaje del host, ≤ 60 caracteres) y fecha de última actividad, y permitir retomar cualquiera.
- **FR-008**: "Nueva conversación" MUST empezar una conversación vacía sin borrar las anteriores.
- **FR-009**: Solo se muestran mensajes del host y del asistente; nunca los de sistema o herramientas.
- **FR-010**: Tras una respuesta que aplicó un cambio, la app MUST refrescar los datos de la pantalla de fondo.
- **FR-011**: Textos nuevos en es/en/pt.

### Key Entities

- **Conversación** (existente): id, título (derivado del primer mensaje del host), última actividad.
- **Mensaje** (existente): rol (host/asistente), texto, fecha.
- **Propuesta pendiente** (existente `AgentAction` en estado `proposed`).

## Success Criteria *(mandatory)*

- **SC-001**: Desde cualquier sección, el host abre el asistente en 1 clic o con Ctrl+K y lo cierra con Esc.
- **SC-002**: 100 % de los mensajes escritos en el panel aparecen en la sección Chat y viceversa, también tras recargar.
- **SC-003**: Una propuesta pendiente sobrevive a la recarga y se puede confirmar.
- **SC-004**: El historial muestra las conversaciones recientes y cualquiera se puede retomar.

## Assumptions

- Single-tenant: todas las conversaciones son del host.
- No se agrega contexto automático de la pantalla actual (fuera de alcance según la issue).
- El historial no se pagina (máx. 20 recientes).
