# Feature Specification: Calendario con promociones y deals nativos visibles + registro manual de deals

**Feature Branch**: `015-calendar-offers`
**Created**: 2026-07-03
**Status**: Draft
**Input**: Issue #94 — El host quiere ver de un vistazo qué días están en oferta: tanto las promociones de precio creadas desde la app como los deals nativos de los canales (badge de Booking, descuentos semanal/mensual de Airbnb). Los deals nativos no se pueden leer por API (verificado en features 009/011/013), así que hoy son invisibles para la app y la advertencia de doble descuento es un texto genérico. Decisión del host (2026-07-03): registro manual liviano — al crear/desactivar un deal en el panel del canal, lo anota en la app en ~10 segundos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar los deals nativos de los canales (Priority: P1)

Como host, quiero anotar en la app los deals nativos que gestiono en los paneles de Booking/Airbnb (canal, nombre, descuento, fechas o "siempre activo", activo sí/no), para que la app sepa que existen y pueda mostrármelos y advertirme, sin pretender gestionarlos por ella.

**Why this priority**: es el dato base de toda la feature; sin registro no hay marcado ni advertencia real. Es la decisión ya tomada con el host.

**Independent Test**: crear un deal desde la sección Ofertas (p. ej. "Vacaciones Julio", Booking, 20%, 3–31 jul), verlo en la lista, editarlo, desactivarlo y reactivarlo, y borrarlo; verificar que nada de esto toca el canal (registro informativo local).

**Acceptance Scenarios**:

1. **Given** la sección Ofertas, **When** el host registra un deal nativo con canal, nombre, % de descuento y rango de fechas, **Then** el deal aparece en la lista de deals registrados con todos sus datos.
2. **Given** un descuento "siempre activo" (p. ej. semanal/mensual de Airbnb), **When** el host lo registra sin fechas, **Then** el sistema lo acepta como rango abierto y lo muestra como "siempre activo".
3. **Given** un deal registrado, **When** el host lo edita, desactiva, reactiva o borra, **Then** el cambio se refleja de inmediato en la lista y en el calendario — y ninguna de estas operaciones escribe nada al canal.
4. **Given** datos incompletos o inválidos (sin nombre, canal desconocido, descuento fuera de 0–100, fechas invertidas), **When** el host intenta guardar, **Then** el sistema lo rechaza con un mensaje claro.
5. **Given** la guía existente de la sección Ofertas, **When** el host la lee, **Then** entiende que el deal se crea/gestiona en el panel del canal (deep-links existentes) y que aquí solo se ANOTA para visibilidad y advertencias.

---

### User Story 2 - Ver los días en oferta en el calendario (Priority: P1)

Como host, quiero que el calendario marque los días cubiertos por promociones de la app y por deals nativos activos, con marcadores distinguibles entre sí y de los existentes (sugerencia, reserva, bloqueo), para tener el panorama de ofertas de un vistazo.

**Why this priority**: es el objetivo del issue ("panorama general de un vistazo"); junto con la US1 forma el mínimo valioso.

**Independent Test**: con una promo de la app y un deal nativo registrados en rangos distintos, abrir el calendario y verificar que cada rango muestra su marcador correspondiente y la leyenda los distingue; sin promos ni deals, el calendario se ve idéntico al actual.

**Acceptance Scenarios**:

1. **Given** una promoción de la app activa que cubre un rango, **When** el host abre el calendario, **Then** esos días muestran el marcador de promoción (comportamiento existente que se conserva).
2. **Given** un deal nativo ACTIVO registrado con rango de fechas, **When** el host abre el calendario, **Then** los días del rango muestran un marcador de deal nativo distinguible del de promoción de la app y de los demás marcadores, y la leyenda lo identifica.
3. **Given** un deal nativo "siempre activo" (rango abierto), **When** el host navega a cualquier mes, **Then** todos los días con datos muestran su marcador.
4. **Given** un deal desactivado o borrado, **When** el host mira el calendario, **Then** sus días ya no se marcan.
5. **Given** un día con promoción de la app + deal nativo + sugerencia a la vez, **When** el host lo mira, **Then** los marcadores conviven sin ocultarse.

---

### User Story 3 - Ver el detalle de ofertas del día al clic (Priority: P2)

Como host, quiero hacer clic en un día en oferta y ver en el panel lateral qué aplica exactamente ese día — promociones de la app (nombre, descuento, alcance de canales) y deals nativos (nombre, canal, descuento, si es siempre-activo) — para saber qué está descontando cada canal sin ir a los paneles.

**Why this priority**: completa el flujo "ver → entender"; sin él, el marcador dice "hay algo" pero no qué.

**Independent Test**: clic en un día cubierto por una promo y un deal; el panel muestra ambos con sus datos; clic en un día sin ofertas no muestra el panel de ofertas.

**Acceptance Scenarios**:

1. **Given** un día con ofertas (promo de la app y/o deal nativo), **When** el host hace clic, **Then** el panel lateral lista cada una con: tipo (promoción de la app / deal nativo), nombre, descuento, canal o alcance de canales, y rango de vigencia (o "siempre activo").
2. **Given** un día sin ofertas, **When** el host hace clic, **Then** no aparece panel de ofertas (los paneles existentes — editor de rango, sugerencias, precio por canal — se comportan como hoy).
3. **Given** el panel de ofertas y el de sugerencias aplican al mismo día, **When** el host hace clic, **Then** ambos conviven en la columna lateral sin interferirse.

---

### User Story 4 - Advertencia de doble descuento real (Priority: P2)

Como host, quiero que al previsualizar una promoción de precio la advertencia de doble descuento sea una comprobación real contra mis deals registrados — nombrando el deal concreto que solapa en fechas y canal — para no repetir el error caro del doble descuento (ya me pasó con el deal de julio), y no ver advertencias falsas cuando no hay solape.

**Why this priority**: convierte una advertencia decorativa en una protección real; depende de la US1.

**Independent Test**: previsualizar una promo que solapa con un deal registrado activo → la advertencia nombra el deal; previsualizar una sin solape (fechas o canal distintos, o deal inactivo) → sin advertencia de doble descuento.

**Acceptance Scenarios**:

1. **Given** un deal nativo ACTIVO de Booking que cubre 3–31 jul, **When** el host previsualiza una promoción de la app para 10–15 jul con alcance que incluye Booking, **Then** la advertencia dice que puede duplicarse con ese deal, con su nombre, canal y descuento.
2. **Given** el mismo deal, **When** la promoción se limita a "solo Airbnb" (alcance de canales), **Then** NO aparece advertencia de doble descuento por ese deal.
3. **Given** el deal está desactivado o sus fechas no solapan, **When** el host previsualiza, **Then** no hay advertencia de doble descuento (cero falsas alarmas).
4. **Given** varios deals solapan, **When** el host previsualiza, **Then** la advertencia los nombra todos.
5. **Given** un deal "siempre activo", **When** cualquier promoción incluye su canal, **Then** la advertencia aparece siempre (el rango abierto solapa con todo).

---

### User Story 5 - Semilla con los deals reales del host (Priority: P3)

Como host, quiero que los 3 deals que ya tengo activos queden registrados al estrenar la feature — "Vacaciones Julio" (Booking, 20%, 3–31 jul, mín 3 noches), descuento semanal (Airbnb, 5%, siempre activo) y mensual (Airbnb, 25%, siempre activo) — para que el calendario y las advertencias arranquen reflejando la realidad.

**Why this priority**: es carga de datos, no funcionalidad; requiere confirmación del host de los valores.

**Independent Test**: tras la carga (confirmada por el host), la lista muestra los 3 deals y el calendario de julio marca los días 3–31 con deal de Booking y todos los días con los de Airbnb.

**Acceptance Scenarios**:

1. **Given** la feature desplegada, **When** se registran los 3 deals conocidos (con confirmación del host de los valores), **Then** aparecen en la lista y el calendario los refleja.

---

### Edge Cases

- **Deal sin fechas (siempre activo)**: rango abierto; solapa con cualquier promoción de su canal y se marca en todos los meses.
- **Deal solo con fecha de inicio o solo de fin**: medio-abierto; el solape y el marcado respetan el extremo definido.
- **Fechas invertidas** (fin < inicio): rechazado con mensaje claro.
- **Deal que venció** (fecha fin en el pasado): deja de marcarse en meses futuros y no genera advertencias para promociones futuras; sigue visible en la lista (historia) hasta que el host lo borre.
- **Doble registro del mismo deal**: se permite (el sistema no puede verificar contra el canal), pero la lista lo hace visible para que el host lo depure.
- **Promoción sin alcance definido (todos los canales)**: solapa con deals de cualquier canal.
- **Día con todos los marcadores a la vez** (promo + deal + sugerencia + reserva/bloqueo): conviven sin ocultarse.
- **Sin deals registrados y sin promos**: el calendario y las respuestas existentes quedan idénticos al comportamiento actual.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El host MUST poder registrar deals nativos con: canal (booking/airbnb), nombre, porcentaje de descuento, rango de fechas opcional (abierto, medio-abierto o cerrado) y estado activo/inactivo.
- **FR-002**: El registro MUST ser puramente informativo/local: ninguna operación sobre deals escribe al canal; la gestión real sigue en los paneles (deep-links existentes) y la guía de Ofertas lo deja claro.
- **FR-003**: El host MUST poder listar, editar, desactivar/reactivar y borrar deals registrados, con validación (nombre requerido, canal válido, descuento 0–100, fechas coherentes) y mensajes claros.
- **FR-004**: El calendario MUST marcar los días cubiertos por deals nativos ACTIVOS con un marcador distinguible del de promociones de la app y de los marcadores existentes (sugerencia, reserva, bloqueo), con leyenda; un deal inactivo no marca nada y un deal solo marca los días que su vigencia cubre (al vencer deja de marcar días futuros; los días pasados del mes visible conservan la marca, igual que las promociones de la app).
- **FR-005**: El marcado existente de promociones de la app MUST conservarse; ambos tipos conviven en el mismo día sin ocultarse (también con sugerencias y estados de disponibilidad).
- **FR-006**: Al hacer clic en un día en oferta, el host MUST ver el detalle de TODO lo que aplica ese día: promociones de la app (nombre, descuento, alcance de canales) y deals nativos (nombre, canal, descuento, vigencia o "siempre activo").
- **FR-007**: La previsualización (y la propuesta del agente) de una promoción de precio MUST comprobar el solape real contra los deals registrados — solape de fechas Y de canal (considerando el alcance de canales de la promoción) Y deal activo — y nombrar cada deal concreto en la advertencia; sin solape MUST NOT haber advertencia de doble descuento.
- **FR-008**: Un deal "siempre activo" (sin fechas) MUST tratarse como solapante con cualquier rango y marcarse en todos los días con datos del calendario.
- **FR-009**: Los 3 deals reales conocidos del host MUST quedar registrados al estrenar la feature, previa confirmación del host de sus valores.
- **FR-010**: Sin deals registrados, el comportamiento actual MUST permanecer idéntico (calendario, promociones — sin falsas alarmas de doble descuento).

### Key Entities

- **Deal nativo (NativeDeal)** — NUEVA: registro informativo de un descuento gestionado en el panel del canal. Canal, nombre, % de descuento, rango de fechas opcional (soporta abierto/medio-abierto), activo sí/no. Sin vínculo con el canal manager.
- **Promoción (Promotion)** — existente: sin cambios de estructura; su previsualización gana la comprobación real de solape.
- **Día del calendario (vista)** — existente: gana la información derivada "deals nativos activos que cubren este día" y el detalle de promociones (nombre → nombre+descuento+alcance) para el panel del clic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host registra un deal nativo en menos de 30 segundos desde la sección Ofertas.
- **SC-002**: El 100% de los días cubiertos por deals activos — y solo esos — muestran el marcador de deal en el calendario; los desactivados/vencidos desaparecen del marcado de inmediato.
- **SC-003**: El 100% de las previsualizaciones de promoción con solape real (fechas+canal+activo) nombran el deal concreto; 0 advertencias de doble descuento cuando no hay solape.
- **SC-004**: Con el registro vacío, el calendario y las respuestas de promociones son equivalentes al comportamiento actual (los 187 tests existentes siguen verdes).
- **SC-005**: Los 3 deals reales del host quedan registrados y visibles en el calendario al cerrar la feature.

## Assumptions

- Single-tenant: el registro es del único host; no hay permisos ni multiusuario.
- El registro NO se valida contra el canal (no hay API para leer deals): la veracidad depende del host; la lista visible facilita depurar duplicados u obsoletos.
- "Activo" del deal es el interruptor del registro local; el host es responsable de mantenerlo alineado con el panel del canal (10 segundos por cambio, decisión aceptada).
- Los deals de Booking con badge y los descuentos semanal/mensual de Airbnb se modelan igual (canal+nombre+%+vigencia); detalles como "mín. noches" caben en el nombre (p. ej. "Vacaciones Julio · mín 3").
- El marcador de deal nativo indica el canal a nivel de detalle (panel del clic); en la celda del día basta distinguir "deal nativo" de "promo de la app" (el espacio es limitado y el detalle está a un clic).
- La advertencia genérica actual de doble descuento se sustituye por la comprobación real (con registro vacío no hay advertencia — el host registra sus deals en la semilla).
- El human-in-the-loop no cambia: las escrituras al canal siguen siendo solo las de promociones de la app con su preview→confirmar; el registro de deals es local.
- Fuera de alcance: leer/escribir deals por API (no existe), notas del host (#96), motor de sugerencias (#98).
