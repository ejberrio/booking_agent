# Feature Specification: Uso y límites de IA por cuenta

**Feature Branch**: `027-ai-usage-limits`
**Created**: 2026-10-14
**Status**: Draft
**Input**: Issue #144 (Feature 027, épica #156 Comercial Fase 0). La IA (asistente, extracción de eventos y mercado, búsquedas web) la paga la plataforma; con varios anfitriones hay que medirla y limitarla por cuenta.

## Decisiones del host (2026-10-14)

1. **300 mensajes al asistente por mes** por cuenta durante la beta; el administrador lo puede cambiar por cuenta.
2. Al llegar al límite, el asistente **se pausa hasta el próximo mes** con un mensaje claro; aviso previo al 80 %. Las sugerencias diarias y aprobar/rechazar siguen funcionando, y **nunca se corta una escritura pendiente de confirmar** (la respuesta de confirmación del anfitrión siempre se atiende).
3. **Tope de 5 búsquedas web por cuenta al día** en el escaneo diario (eventos y mercado); el administrador lo puede subir por cuenta.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Medir el uso y el costo por cuenta (Priority: P1)

Cada llamada a la IA (asistente o escaneo) y cada búsqueda web queda registrada en la cuenta que la originó, por día, con el modelo, los tokens de entrada y salida y un costo estimado en dólares.

**Independent Test**: enviar mensajes al asistente y correr el escaneo de una cuenta; el registro del día muestra llamadas, tokens, búsquedas y costo de esa cuenta y de ninguna otra.

**Acceptance Scenarios**:
1. **Given** un mensaje al asistente que hace 2 llamadas a la IA, **When** termina, **Then** el uso del día suma 1 mensaje, 2 llamadas y sus tokens y costo.
2. **Given** el escaneo diario de una cuenta, **When** termina, **Then** se registran sus llamadas de extracción/mercado y sus búsquedas web.
3. **Given** un modelo sin precio configurado, **When** se registra su uso, **Then** los tokens se guardan y el costo queda en 0 marcado como "sin precio".

### User Story 2 - Límite mensual del asistente (Priority: P1)

El anfitrión ve cuántos mensajes le quedan este mes. Al pasar el 80 % ve un aviso; al llegar al 100 % el asistente responde que alcanzó el límite y cuándo se renueva, sin gastar IA.

**Independent Test**: con el límite en 3, el tercer mensaje funciona y muestra el aviso; el cuarto recibe el mensaje de límite sin llamar a la IA; con una acción pendiente de confirmar, la confirmación se atiende aunque esté en el límite.

**Acceptance Scenarios**:
1. **Given** 299 mensajes usados de 300, **When** envía uno más, **Then** se atiende y se le avisa que llegó al límite.
2. **Given** 300 de 300, **When** envía otro, **Then** recibe "Alcanzaste el límite de mensajes de este mes; se renueva el 1 de <mes>" y no se llama a la IA.
3. **Given** el límite alcanzado y un cambio pendiente de confirmar, **When** responde "sí", **Then** la confirmación se procesa.
4. **Given** el primer día del mes siguiente, **When** escribe, **Then** el contador empieza de cero.

### User Story 3 - Tope diario de búsquedas del escaneo (Priority: P2)

El escaneo diario de cada cuenta hace como máximo N búsquedas web (5 por defecto); las consultas que sobran se omiten ese día y quedan anotadas en la corrida. Los eventos de la ciudad ya buscados por otra cuenta se reutilizan.

**Acceptance Scenarios**:
1. **Given** una configuración de 8 consultas y tope 5, **When** corre el escaneo, **Then** se hacen 5 búsquedas y la corrida indica que se omitieron 3.
2. **Given** tope agotado, **When** se generan sugerencias, **Then** se generan igual con los datos disponibles.

### User Story 4 - Panel del administrador (Priority: P2)

El administrador ve, para el mes elegido, por cuenta: mensajes al asistente, llamadas a la IA, tokens, búsquedas y costo estimado, más el total de la plataforma; y puede cambiar los límites de una cuenta.

**Acceptance Scenarios**:
1. **Given** el panel, **When** abre "Uso de IA", **Then** ve una fila por cuenta y el total del mes.
2. **Given** una cuenta, **When** el administrador sube su límite a 600, **Then** esa cuenta puede seguir usando el asistente.
3. **Given** el panel de uso, **When** se revisa, **Then** no aparece contenido de conversaciones ni nombres de huéspedes.

### Edge Cases

- La IA falla a mitad de un mensaje: se registra lo que sí se consumió; el mensaje cuenta igual.
- Sin LLM configurado: no se registra uso de IA.
- Cambio de mes a mitad de una conversación: cuenta en el mes en que se envía.
- El límite se baja por debajo de lo ya usado: queda pausado hasta el mes siguiente.
- Cuenta eliminada: su uso se borra con ella; el total de plataforma de meses pasados puede bajar (aceptado).

## Requirements *(mandatory)*

- **FR-001**: El sistema MUST registrar por cuenta y día: mensajes al asistente, llamadas a la IA por tipo (asistente/escaneo) y modelo, tokens de entrada y salida, búsquedas web y costo estimado.
- **FR-002**: El costo MUST calcularse con una tabla de precios por modelo (USD por millón de tokens) y por búsqueda, configurable sin cambiar código.
- **FR-003**: Cada cuenta MUST tener un límite mensual de mensajes al asistente (por defecto 300) y un tope diario de búsquedas (por defecto 5), modificables por el administrador.
- **FR-004**: Al alcanzar el límite mensual, el asistente MUST responder un mensaje de límite con la fecha de renovación, sin llamar a la IA, salvo que haya una acción pendiente de confirmar.
- **FR-005**: La web MUST mostrar al anfitrión su uso del mes y avisar al 80 % y al 100 %.
- **FR-006**: El escaneo diario MUST respetar el tope diario de búsquedas por cuenta y anotar las consultas omitidas.
- **FR-007**: El administrador MUST ver el uso y costo por cuenta y mes, y el total de la plataforma; sin contenido de conversaciones ni datos de huéspedes.
- **FR-008**: El uso MUST quedar aislado por cuenta (principio VI) y borrarse con la cuenta.

### Key Entities

- **Uso de IA (diario)**: cuenta, día, tipo (chat_message, chat, scan, search), modelo, llamadas, tokens de entrada, tokens de salida, costo estimado.
- **Límites de la cuenta**: mensajes al mes, búsquedas al día (vacío = valor por defecto de la plataforma).

## Success Criteria *(mandatory)*

- **SC-001**: El 100 % de las llamadas a la IA y búsquedas web quedan atribuidas a una cuenta.
- **SC-002**: Ninguna cuenta supera su límite mensual de mensajes ni su tope diario de búsquedas (verificado por pruebas).
- **SC-003**: El administrador conoce el costo estimado del mes por cuenta en menos de 1 minuto.
- **SC-004**: 0 escrituras pendientes interrumpidas por el límite.

## Assumptions

- Precios iniciales: gpt-6-luna USD 0,10 / 0,50 por millón de tokens (entrada/salida); gpt-4o-mini 0,15 / 0,60; gpt-4o 2,50 / 10; búsqueda web USD 0,008. Ajustables por variable de entorno.
- El mes y el día se cuentan en hora de Colombia (UTC−5).
- Los planes con cobro llegan con #152; aquí solo hay límites por cuenta.
