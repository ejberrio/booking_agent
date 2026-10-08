# Feature Specification: Reservas en tiempo real (avisos de Beds24)

**Feature Branch**: `020-beds24-webhooks`
**Created**: 2026-10-08
**Status**: Draft
**Input**: User description: "Webhooks de Beds24: reservas y cancelaciones en tiempo real (Feature 020, issue #117)."

## Contexto

Hoy StayLever se entera de reservas nuevas, modificaciones y cancelaciones **solo cuando sincroniza**: una vez al día (proceso automático), o cuando el host pulsa "Sincronizar" o se lo pide al chat. Entre sincronizaciones, el calendario, las noches vendibles de la pestaña Sugerencias (feature 019) y el chat pueden trabajar con datos viejos. Caso real: una cancelación de agosto no se reflejó durante días y además impidió re-bloquear esas fechas.

El Channel Manager puede **avisar** a una dirección cuando cambia una reserva. Esta función hace que StayLever reciba esos avisos y se actualice sola en alrededor de un minuto, manteniendo la sincronización diaria como red de seguridad.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Las reservas aparecen solas (Priority: P1)

Como host, cuando entra una reserva nueva, se modifica o se cancela en Booking.com o Airbnb, quiero que StayLever lo refleje en alrededor de un minuto sin que yo tenga que pulsar "Sincronizar".

**Why this priority**: es el valor completo de la función; sin esto el resto no aporta.

**Independent Test**: crear una reserva de prueba en el Channel Manager (o recibir una real) y verificar que en ≤ 2 minutos aparece en el calendario (noches en rojo) y desaparecen las sugerencias de esas noches; cancelarla y verificar que las noches vuelven a estar libres y las sugerencias reaparecen.

**Acceptance Scenarios**:

1. **Given** el host no está usando la app, **When** entra una reserva nueva, **Then** en ≤ 2 minutos la reserva figura en StayLever con sus fechas, canal y huésped, y sus noches aparecen ocupadas en el calendario.
2. **Given** una reserva existente, **When** se cancela en el canal, **Then** en ≤ 2 minutos queda cancelada en StayLever y sus noches vuelven a estar libres (y vendibles en Sugerencias).
3. **Given** una reserva existente, **When** se cambian sus fechas, **Then** en ≤ 2 minutos StayLever muestra las fechas nuevas y libera las noches que ya no ocupa.
4. **Given** llega un aviso, **When** se procesa, **Then** no se publica ningún precio ni disponibilidad al canal (solo se lee y se actualiza StayLever).

---

### User Story 2 - Solo avisos auténticos (Priority: P1)

Como host quiero que solo el Channel Manager pueda actualizar mis reservas por esta vía: un aviso falso o sin la clave secreta debe ignorarse sin ningún efecto.

**Why this priority**: la dirección de avisos es pública por naturaleza; sin autenticación, cualquiera podría inyectar reservas falsas y bloquear ventas.

**Independent Test**: enviar avisos sin clave, con clave incorrecta y con la clave correcta; solo el último produce cambios.

**Acceptance Scenarios**:

1. **Given** un aviso sin clave o con clave incorrecta, **When** llega, **Then** se rechaza, no cambia ningún dato y queda contado como rechazado (sin guardar su contenido).
2. **Given** el host todavía no configuró la clave, **When** llega cualquier aviso, **Then** se rechaza (la función está desactivada hasta configurarla).
3. **Given** el host rota la clave en Ajustes → Secretos, **When** llega un aviso con la clave anterior, **Then** se rechaza; con la nueva, se acepta, sin reiniciar nada.

---

### User Story 3 - Robusto ante duplicados, desorden y caídas (Priority: P2)

Como host quiero que los datos de reservas sean siempre correctos aunque los avisos lleguen repetidos, en desorden, se reintenten, vengan incompletos o dejen de llegar.

**Why this priority**: los sistemas de avisos reintentan y pueden fallar; datos inconsistentes de reservas son peores que datos un poco atrasados.

**Independent Test**: enviar el mismo aviso dos veces, enviar "modificada" antes que "nueva", enviar un aviso con datos mínimos; en todos los casos el estado final coincide con el del Channel Manager.

**Acceptance Scenarios**:

1. **Given** el mismo aviso llega dos veces, **When** se procesan, **Then** el resultado es idéntico a procesarlo una vez (sin reservas duplicadas).
2. **Given** avisos de la misma reserva llegan en desorden, **When** se procesan, **Then** el estado final refleja el estado vigente en el Channel Manager.
3. **Given** un aviso trae solo el identificador de la reserva (o datos incompletos), **When** se procesa, **Then** StayLever consulta al Channel Manager la reserva/rango y se actualiza con el dato vigente.
4. **Given** el Channel Manager no responde al procesar un aviso, **When** falla, **Then** el aviso queda registrado como fallido, el host lo ve en el estado, y la siguiente sincronización (diaria, botón o chat) corrige el dato.
5. **Given** los avisos dejan de llegar (mal configurados o caídos), **When** pasa el día, **Then** la sincronización diaria sigue actualizando las reservas igual que hoy.

---

### User Story 4 - Ver que funciona y saber configurarlo (Priority: P2)

Como host quiero ver en Ajustes si los avisos están llegando (último aviso, cuántos se aceptaron/rechazaron/fallaron) y tener una guía paso a paso para configurar la dirección en el Channel Manager.

**Why this priority**: la configuración en el Channel Manager es un paso manual; sin visibilidad, el host no sabe si quedó bien.

**Independent Test**: con la función sin configurar, Ajustes muestra "sin configurar" y la guía; tras configurar y recibir un aviso, muestra "funcionando" con la hora del último aviso.

**Acceptance Scenarios**:

1. **Given** no hay clave configurada, **When** el host abre Ajustes, **Then** ve "Avisos en tiempo real: sin configurar" y la guía con la dirección exacta a copiar.
2. **Given** avisos recibidos, **When** abre Ajustes, **Then** ve la hora del último aviso aceptado y conteos recientes (aceptados, rechazados, fallidos).
3. **Given** la clave está configurada pero no ha llegado ningún aviso en 7 días, **When** abre Ajustes, **Then** ve un aviso de "sin actividad: revisa la configuración" (sin alarmar si simplemente no hubo reservas).
4. **Given** la guía, **When** el host la sigue, **Then** puede configurar la dirección en el Channel Manager sin ayuda técnica, y la clave nunca se muestra completa en pantalla después de guardarla.

---

### Edge Cases

- Aviso de una propiedad o unidad que no es la del host: se ignora (cuenta como aceptado sin cambios).
- Aviso de una reserva fuera del horizonte que StayLever sincroniza (p. ej. dentro de 2 años): se procesa igual.
- Muchos avisos seguidos (p. ej. el Channel Manager reenvía varios al reconectar): todos se procesan sin bloquear la app.
- Aviso que llega mientras corre la sincronización diaria: el resultado final es consistente (ambos llegan al mismo estado).
- Reserva cancelada cuyas noches el host quería mantener bloqueadas: los bloqueos manuales del host no se tocan; solo cambia la reserva.
- Nombre del huésped: se guarda como hoy (visible solo dentro de la app) y nunca aparece en registros ni en el estado de los avisos.
- Clave rota o borrada mientras llegan avisos: desde ese momento se rechazan.

## Requirements *(mandatory)*

### Functional Requirements

**Recepción y actualización (US1)**

- **FR-001**: El sistema MUST ofrecer una dirección pública donde el Channel Manager pueda enviar avisos de reservas (nueva, modificada, cancelada).
- **FR-002**: Al aceptar un aviso, el sistema MUST actualizar la reserva afectada en StayLever (fechas, estado, canal, huésped) y la ocupación derivada, dejando el resultado visible en el calendario y en Sugerencias en ≤ 2 minutos desde el aviso.
- **FR-003**: Procesar un aviso MUST NOT publicar precios ni disponibilidad al canal ni modificar bloqueos manuales del host.
- **FR-004**: La fuente de verdad MUST ser el Channel Manager: el sistema actualiza con el estado vigente de la reserva (consultándolo si el aviso no lo trae completo).

**Autenticación (US2)**

- **FR-005**: Un aviso MUST aceptarse solo si presenta la clave secreta configurada por el host; si falta, es incorrecta o no hay clave configurada, MUST rechazarse sin efectos.
- **FR-006**: La clave MUST gestionarse como los demás secretos (Ajustes → Secretos: write-only, rotación inmediata, nunca en registros ni en el repositorio).
- **FR-007**: Los avisos rechazados MUST contarse sin guardar su contenido.

**Robustez (US3)**

- **FR-008**: Procesar el mismo aviso varias veces MUST producir el mismo resultado que procesarlo una vez.
- **FR-009**: El orden de llegada de los avisos MUST NOT afectar el estado final (se aplica el estado vigente).
- **FR-010**: Si el procesamiento falla (Channel Manager caído u otro error), el aviso MUST quedar registrado como fallido y la sincronización existente (diaria, botón, chat) MUST seguir corrigiendo los datos.
- **FR-011**: La recepción MUST responder rápido al Channel Manager para no provocar reintentos innecesarios.

**Visibilidad (US4)**

- **FR-012**: Ajustes MUST mostrar el estado de los avisos: sin configurar / funcionando / sin actividad reciente, la hora del último aviso aceptado y conteos recientes de aceptados, rechazados y fallidos.
- **FR-013**: Ajustes MUST incluir una guía para configurar la dirección en el Channel Manager, con la dirección exacta a copiar.
- **FR-014**: El estado de avisos MUST NOT mostrar datos personales de huéspedes.

**Privacidad**

- **FR-015**: Los registros de la aplicación MUST NOT incluir el nombre del huésped, la clave secreta ni el contenido de los avisos.

### Key Entities

- **Aviso de reserva** (registro mínimo): cuándo llegó, resultado (aceptado, rechazado, fallido, sin cambios), referencia de la reserva afectada y motivo del fallo si aplica; sin contenido del aviso ni datos del huésped.
- **Reserva** (existente): fechas, estado, canal, referencia externa y nombre del huésped (solo visible en la app).
- **Clave de avisos** (secreto): valor que el Channel Manager presenta en cada aviso; gestionado en Ajustes → Secretos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 95 % de las reservas nuevas, modificaciones y cancelaciones se reflejan en StayLever en ≤ 2 minutos, sin acción del host.
- **SC-002**: 0 cambios de datos producidos por avisos sin clave o con clave incorrecta.
- **SC-003**: Recibir el mismo aviso N veces produce 0 reservas duplicadas.
- **SC-004**: Si los avisos fallan o dejan de llegar, las reservas quedan correctas como máximo en la siguiente sincronización diaria (igual que hoy).
- **SC-005**: El host puede comprobar desde Ajustes, en menos de 10 segundos, si los avisos funcionan.
- **SC-006**: 0 apariciones de nombres de huéspedes o de la clave en los registros de la aplicación.

## Assumptions

- El Channel Manager (Beds24) permite configurar una dirección de avisos de reservas y enviar con ella un valor secreto (en la dirección o en una cabecera); si no se puede configurar por su API, el host lo hace una vez desde el panel siguiendo la guía de la app.
- Solo la web es pública; la recepción de avisos entra por la web y se reenvía a la API privada (patrón del proxy existente), sin exponer la API.
- La sincronización diaria, el botón "Sincronizar" y la herramienta del chat se mantienen sin cambios como red de seguridad.
- Single-tenant: una propiedad y una unidad; los avisos de otras propiedades se ignoran.
- "Visible en ≤ 2 minutos" se mide al abrir o volver a la página (la app se refresca al recuperar el foco); el refresco continuo de una página abierta queda fuera de alcance.
- La latencia objetivo (≤ 2 minutos) depende de que el Channel Manager envíe el aviso con prontitud; StayLever procesa cada aviso en segundos.
