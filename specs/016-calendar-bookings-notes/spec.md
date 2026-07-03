# Feature Specification: Detalle de reservas y notas del host en el calendario

**Feature Branch**: `016-calendar-bookings-notes`
**Created**: 2026-07-03
**Status**: Draft
**Input**: Issue #96 — Al hacer clic en un día del calendario el host no ve nada sobre la reserva que lo ocupa (quién llega, cuándo sale, por qué canal) ni puede dejar constancia de por qué bloqueó un rango (típico: "reserva personal de Fulano" — hoy esa información vive en su memoria). El Channel Manager sí reporta el nombre del huésped, pero la app no lo captura.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver el detalle de la reserva al clic (Priority: P1)

Como host, quiero hacer clic en un día reservado y ver quién lo ocupa — nombre del huésped (si el canal lo dio), canal de origen, llegada → salida, noches, estado y referencia — para responder "¿quién llega ese día?" sin entrar a Beds24 ni a los paneles de los canales.

**Why this priority**: es la pregunta más frecuente del host frente al calendario y hoy no tiene respuesta en la app.

**Independent Test**: con una reserva importada que cubre un rango, clic en un día del rango → el panel muestra sus datos; un día sin reserva no muestra panel de reservas.

**Acceptance Scenarios**:

1. **Given** una reserva que cubre el día, **When** el host hace clic, **Then** el panel lateral muestra: nombre del huésped (si existe), canal de origen, llegada → salida, número de noches, estado y referencia externa.
2. **Given** una reserva sin nombre de huésped (el canal no lo dio), **When** el host la consulta, **Then** el panel lo muestra honesto ("sin nombre") en lugar de ocultar la reserva o inventar un dato.
3. **Given** un día con salida de una reserva y llegada de otra (la noche pertenece a la que llega), **When** el host hace clic, **Then** ve la(s) reserva(s) cuya estancia incluye esa NOCHE (no la que sale ese día).
4. **Given** un día sin reservas, **When** el host hace clic, **Then** no aparece panel de reservas y los paneles existentes se comportan como hoy.

---

### User Story 2 - Capturar el nombre del huésped en el import (Priority: P1)

Como host, quiero que el import de reservas capture el nombre del huésped que reporta el Channel Manager — y lo corrija en re-imports para las reservas ya existentes — para que el detalle del día tenga la información completa sin pasos manuales.

**Why this priority**: sin el dato, la US1 muestra "sin nombre" para todo; es el habilitador del valor principal.

**Independent Test**: importar reservas con dobles que reportan nombre → la reserva local lo guarda; re-importar con nombre corregido → la reserva existente se actualiza; un canal que no da nombre deja el campo vacío sin romper el import.

**Acceptance Scenarios**:

1. **Given** el Channel Manager reporta el nombre del huésped, **When** se importan reservas, **Then** las nuevas quedan con su nombre.
2. **Given** una reserva ya importada sin nombre (histórica), **When** se re-importa y el canal ahora reporta nombre, **Then** la reserva existente se corrige (patrón de corrección de históricos ya usado para el canal).
3. **Given** un canal/proveedor que no reporta nombre, **When** se importa, **Then** el import completa sin errores y el campo queda vacío.
4. **Given** el dato es personal, **When** se muestra, **Then** solo aparece dentro de la app (single-tenant); no se envía a terceros ni aparece en logs.

---

### User Story 3 - Notas del host sobre días o rangos (Priority: P1)

Como host, quiero anotar texto libre sobre un día o un rango (típico: el porqué de un bloqueo — "reserva personal de Fulano") y poder editarlo o borrarlo, para que esa información deje de vivir en mi memoria.

**Why this priority**: es la segunda mitad del issue; independiente de las reservas (funciona incluso donde no hay reserva, p. ej. bloqueos).

**Independent Test**: crear una nota sobre un rango, verla, editarla y borrarla; las notas nunca tocan el Channel Manager.

**Acceptance Scenarios**:

1. **Given** el host selecciona un día o rango en el calendario, **When** escribe una nota y la guarda, **Then** la nota queda asociada a ese rango y visible al volver.
2. **Given** una nota existente, **When** el host la edita o la borra desde el panel del día, **Then** el cambio aplica de inmediato.
3. **Given** varias notas cuyos rangos se solapan, **When** el host consulta un día compartido, **Then** ve TODAS las notas que lo cubren (sin límite artificial).
4. **Given** una nota vacía o un rango invertido, **When** el host intenta guardar, **Then** el sistema lo rechaza con un mensaje claro.
5. **Given** cualquier operación de notas, **When** se ejecuta, **Then** nada se escribe al Channel Manager (dato local).

---

### User Story 4 - Ver las notas en el calendario (Priority: P2)

Como host, quiero que los días con nota tengan su propio indicador en el calendario — conviviendo con los marcadores existentes (reserva, bloqueo, promoción, sugerencia, deal) — y que el panel del día las muestre, para encontrar mis observaciones de un vistazo.

**Why this priority**: cierra el ciclo anotar → reencontrar; depende de la US3.

**Independent Test**: con una nota sobre un rango, esos días muestran el indicador y el clic muestra el texto; al borrarla, el indicador desaparece; sin notas, el calendario se ve idéntico al actual.

**Acceptance Scenarios**:

1. **Given** una nota sobre un rango, **When** el host abre el calendario, **Then** cada día del rango muestra el indicador de nota, distinguible de los demás marcadores y con entrada en la leyenda.
2. **Given** un día con nota + reserva + bloqueo + oferta a la vez, **When** el host lo mira, **Then** los marcadores conviven sin ocultarse.
3. **Given** una nota borrada, **When** el host mira el calendario, **Then** sus días ya no muestran el indicador.
4. **Given** cero notas, **When** el host abre el calendario, **Then** el render es idéntico al comportamiento actual.

---

### Edge Cases

- **Día de salida**: una reserva ocupa las NOCHES [llegada, salida); el día de la salida no cuenta como ocupado por ella (consistente con el resto del sistema).
- **Reservas canceladas**: no aparecen en el detalle del día (solo confirmadas, consistente con la ocupación del calendario).
- **Varias reservas el mismo día** (salida+llegada consecutivas): se muestran las que incluyen la noche.
- **Nombre parcial** (solo nombre o solo apellido): se muestra lo que haya.
- **Notas sobre rangos largos o pasados**: permitidas (una nota histórica sigue siendo consulta válida); el indicador aparece en cualquier mes navegado que el rango cubra.
- **Texto de nota largo**: se acepta hasta un límite razonable y visible; más allá, se rechaza con mensaje claro.
- **Sin notas ni nombres**: comportamiento y render idénticos a los actuales.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST capturar el nombre del huésped reportado por el Channel Manager al importar reservas (nuevas y corrección de existentes en re-imports); si el proveedor no lo reporta, el campo queda vacío sin fallar.
- **FR-002**: Al hacer clic en un día con reserva confirmada cuya estancia incluye esa noche, el host MUST ver: nombre del huésped (o "sin nombre"), canal de origen, llegada → salida, número de noches, estado y referencia externa — para TODAS las reservas que cubren la noche.
- **FR-003**: El nombre del huésped es dato personal: MUST mostrarse solo dentro de la app y MUST NOT aparecer en logs ni enviarse a terceros.
- **FR-004**: El host MUST poder crear una nota de texto libre sobre un día o rango (desde la selección del calendario), y editar/borrar notas existentes desde el panel del día.
- **FR-005**: Las notas MUST validar: texto no vacío y con límite visible, rango coherente (fin ≥ inicio); errores con mensaje claro.
- **FR-006**: Varias notas MUST poder solapar el mismo día; el panel muestra todas las que lo cubren.
- **FR-007**: Ninguna operación de notas MUST tocar el Channel Manager (dato 100% local del host).
- **FR-008**: Los días cubiertos por notas MUST mostrar un indicador propio en el calendario, distinguible de los marcadores existentes y con leyenda; sin notas, el render MUST ser idéntico al actual.
- **FR-009**: El detalle de reservas y las notas MUST obtenerse sin alterar la consulta de calendario existente (las vistas existentes no cambian su respuesta).
- **FR-010**: Sin datos nuevos (cero notas, nombres vacíos), TODO el comportamiento actual MUST permanecer idéntico (los 199 tests existentes siguen verdes).

### Key Entities

- **Reserva (Booking)** — existente: gana el nombre del huésped (opcional). Sin otros cambios.
- **Nota de calendario (CalendarNote)** — NUEVA: unidad, rango de fechas (día único = rango de un día), texto, marcas de tiempo. Dato local sin vínculo con el Channel Manager.
- **Día del calendario (vista, cliente)**: gana las derivadas "reservas que cubren la noche" y "notas que cubren el día".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host responde "¿quién ocupa este día?" en un clic (nombre, canal, fechas, noches) para el 100% de las reservas confirmadas visibles cuyo canal reportó los datos.
- **SC-002**: Tras un re-import, el 100% de las reservas cuyo canal reporta nombre lo tienen guardado (incluidas las históricas).
- **SC-003**: Crear una nota sobre un rango toma menos de 20 segundos desde el calendario; el 100% de los días cubiertos por notas — y solo esos — muestran el indicador.
- **SC-004**: Cero escrituras al Channel Manager originadas por notas o consultas de reservas.
- **SC-005**: Con cero notas y sin nombres, render y respuestas idénticos al comportamiento actual (199 tests verdes).

## Assumptions

- Single-tenant: el nombre del huésped se muestra al único host; no hay requisitos multi-usuario ni de enmascaramiento interno; no se exporta.
- La noche define la ocupación: una reserva cubre [llegada, salida); el día de salida no lo ocupa esa reserva (consistente con KPIs y disponibilidad existentes).
- El detalle muestra reservas confirmadas (las canceladas siguen fuera, como en el resto de la app; su sync es #91).
- Las notas no requieren previsualización/confirmación en dos pasos: son escritura local sin efecto en canales (mismo criterio que el registro de deals de la feature 015). Borrado real permitido.
- Límite de texto de nota: un valor razonable y comunicado (definición exacta en diseño).
- Fuera de alcance: sync de estados/cancelaciones (#91), edición de reservas (la app no escribe reservas), notas sobre otras entidades, motor de sugerencias (#98).
