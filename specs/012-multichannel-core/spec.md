# Feature Specification: Núcleo multi-canal (Booking.com + Airbnb)

**Feature Branch**: `012-multichannel-core`
**Created**: 2026-07-02
**Status**: Draft
**Input**: Issue #87 — La app hoy asume un solo canal (Booking.com) aunque el Channel Manager ya está conectado a Booking y a Airbnb (listing mapeado y verificado en vivo, issue #86). El objetivo es que la app refleje la realidad multi-canal: reservas con su canal real de origen, canal Airbnb registrado como activo, agente conversacional consciente de ambos canales, y estado/dashboard por canal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reservas con su canal real de origen (Priority: P1)

Como host, cuando llega una reserva por Airbnb o por Booking, quiero que la app la registre con el canal por el que llegó, para saber de dónde viene cada huésped y confiar en lo que veo en el calendario y en las respuestas del agente.

**Why this priority**: Es la base de todo lo demás. Hoy TODA reserva importada se etiqueta como "Booking" aunque venga de Airbnb — un dato incorrecto que contamina el calendario, el estado y cualquier análisis futuro. Sin esto, el resto de la feature no tiene datos correctos que mostrar.

**Independent Test**: Simular una importación desde el canal manager con reservas de origen mixto (una de Booking, una de Airbnb, una directa/desconocida) y verificar que cada una queda registrada con su canal correcto. Con datos reales: re-importar y verificar que la reserva real de Booking (ago 6-19) conserva canal Booking.

**Acceptance Scenarios**:

1. **Given** el canal manager devuelve una reserva originada en Airbnb, **When** la app importa reservas, **Then** la reserva queda registrada con canal "Airbnb".
2. **Given** el canal manager devuelve una reserva originada en Booking.com, **When** la app importa reservas, **Then** la reserva queda registrada con canal "Booking".
3. **Given** el canal manager devuelve una reserva cuyo origen no es reconocible (p. ej. creada a mano en el panel), **When** la app importa reservas, **Then** la reserva queda registrada como canal "directo" y la importación NO falla.
4. **Given** existen reservas importadas antes de esta feature con canal incorrecto, **When** se ejecuta una re-importación completa, **Then** las reservas existentes quedan corregidas con su canal real (sin duplicarse).

---

### User Story 2 - Preguntar al agente por canal (Priority: P2)

Como host, quiero preguntarle al agente cosas como "¿qué reservas tengo de Airbnb?" o "¿cuántas reservas me han llegado por Booking este mes?", y que responda distinguiendo los canales; y cuando proponga cambios de precio o disponibilidad, que me recuerde que aplican a ambos canales.

**Why this priority**: El chat es la interfaz principal del producto. Un agente que dice "solo gestiono el canal Booking" cuando Airbnb ya está conectado da información falsa y mina la confianza.

**Independent Test**: Con reservas de ambos canales en la base, preguntar al agente por las reservas de un canal específico y verificar que filtra correctamente; verificar que el agente ya no se presenta como "solo Booking".

**Acceptance Scenarios**:

1. **Given** hay reservas de Booking y de Airbnb registradas, **When** el host pregunta "¿qué reservas tengo de Airbnb?", **Then** el agente responde solo con las reservas de Airbnb, identificando el canal.
2. **Given** el host pregunta por sus reservas sin mencionar canal, **When** el agente responde, **Then** incluye las de todos los canales indicando el canal de cada una.
3. **Given** el host pide un cambio de precio o disponibilidad, **When** el agente presenta la propuesta, **Then** deja claro que el cambio se publica a todos los canales conectados.

---

### User Story 3 - Estado y dashboard por canal (Priority: P3)

Como host, quiero ver en el dashboard y en el estado del sistema qué canales están conectados y cuántas reservas hay de cada uno, para confirmar de un vistazo que ambos canales están funcionando.

**Why this priority**: Es visibilidad/confianza. Valiosa pero depende de que los datos (US1) ya sean correctos.

**Independent Test**: Con reservas de ambos canales, consultar el estado del sistema y abrir el dashboard: ambos muestran los canales activos y el conteo de reservas por canal.

**Acceptance Scenarios**:

1. **Given** Booking y Airbnb están conectados vía el canal manager, **When** el host consulta el estado del sistema, **Then** ve ambos canales listados como activos con sus reservas por canal.
2. **Given** el host abre el dashboard web, **When** carga la vista principal, **Then** ve los canales conectados y la distribución de reservas por canal.
3. **Given** los textos de la aplicación (título, descripciones), **When** el host los lee, **Then** ya no dicen "solo Booking.com" sino que reflejan la gestión multi-canal.

---

### Edge Cases

- **Origen desconocido o nuevo**: el canal manager puede reportar orígenes no contemplados (otro OTA futuro, reservas manuales). Deben mapearse a "directo" (o quedar visibles como no reconocidos) sin romper la importación.
- **Reservas históricas**: las reservas ya importadas tienen canal incorrecto; la corrección es re-importar desde el canal manager (fuente de verdad). No debe crear duplicados ni perder datos locales asociados.
- **Canal desconectado**: si Airbnb se desconecta del canal manager, el estado debe reflejarlo (canal inactivo) sin ocultar sus reservas históricas.
- **Reserva cancelada/modificada**: al re-importar, una reserva que cambió de estado conserva su canal de origen.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST registrar cada reserva importada con su canal real de origen (Booking, Airbnb o directo), tal como lo reporta el canal manager.
- **FR-002**: El sistema MUST mapear orígenes no reconocidos a "directo" sin abortar la importación del lote.
- **FR-003**: El sistema MUST registrar el canal Airbnb como canal activo de la propiedad (además de Booking) cuando está conectado en el canal manager.
- **FR-004**: Una re-importación completa MUST corregir el canal de reservas previamente importadas con canal incorrecto, sin duplicar reservas.
- **FR-005**: El agente conversacional MUST conocer los canales activos y MUST poder filtrar/identificar reservas por canal al responder.
- **FR-006**: El agente MUST indicar, al proponer cambios de precio o disponibilidad, que la publicación aplica a todos los canales conectados.
- **FR-007**: El estado del sistema MUST exponer los canales conectados y el número de reservas por canal.
- **FR-008**: El dashboard web MUST mostrar los canales conectados y la distribución de reservas por canal.
- **FR-009**: Los textos y metadatos de la aplicación MUST reflejar la gestión multi-canal (no "solo Booking.com").
- **FR-010**: El comportamiento actual de precios, disponibilidad y promociones MUST permanecer intacto (publican vía el canal manager a todos los canales, como hoy).

### Key Entities

- **Reserva (Booking)**: ya existe; su atributo de canal de origen pasa de ser un valor fijo ("booking") a reflejar el origen real reportado por el canal manager.
- **Canal (Channel)**: ya existe (tipos: booking, airbnb, direct); pasa a haber un registro activo por cada canal realmente conectado.
- **Estado del sistema**: se enriquece con la lista de canales activos y conteos de reservas por canal.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las reservas importadas quedan registradas con el canal real reportado por el canal manager (verificado con orígenes mixtos).
- **SC-002**: Tras una re-importación, 0 reservas quedan con canal incorrecto y 0 reservas duplicadas.
- **SC-003**: El host obtiene del agente la lista de reservas de un canal específico en una sola pregunta, sin pasos adicionales.
- **SC-004**: El estado del sistema y el dashboard muestran ambos canales activos y sus conteos en menos de 5 segundos de carga.
- **SC-005**: Ninguna referencia de cara al host afirma que la app gestiona únicamente Booking.com.
- **SC-006**: La suite de pruebas existente (109 pruebas) sigue pasando; las nuevas rutas de importación por canal quedan cubiertas por pruebas.

## Assumptions

- El canal manager (Beds24) es la **fuente de verdad** del canal de origen de cada reserva; la app no lo infiere por otros medios.
- Single-tenant: un host, una propiedad, un canal manager — sin cambios de alcance.
- El conector actual con el canal manager ya entrega el dato de origen de la reserva; no se requieren cambios en la integración externa.
- La corrección de datos históricos se hace re-importando desde el canal manager (no edición manual): es idempotente y segura porque la importación existente ya des-duplica por identificador externo.
- Los principios existentes se mantienen: human-in-the-loop para escrituras (esta feature es mayormente lectura/etiquetado), reversibilidad y auditoría.
- El ajuste de precio por canal, promociones por canal, deep-links de Airbnb y scan de mercado Airbnb quedan **fuera de alcance** (Feature 013+, issues #88/#89).
