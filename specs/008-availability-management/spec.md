# Feature Specification: Gestión de disponibilidad (bloquear/abrir fechas)

**Feature Branch**: `008-availability-management`
**Created**: 2026-06-28
**Status**: Draft
**Input**: User description: "Que el host pueda bloquear (cerrar) y abrir (reabrir) fechas o rangos de su unidad, desde el chat (y deseable desde el calendario), publicándose a Booking.com vía el Channel Manager, con propone→confirma, auditoría y sin romper reservas existentes."

## Clarifications

### Session 2026-06-28

- Q: ¿Incluímos el control de bloquear/abrir en el calendario de la web (US3) en esta feature, o solo por chat? → A: Incluir el calendario AHORA (US3 entra en el alcance de esta feature, junto con el chat).
- Q: ¿Cómo se revierte un bloqueo de disponibilidad? → A: "Abrir" es el inverso de "bloquear"; deshacer un bloqueo = reabrir. No se expone un rollback puntual aparte. Todo queda auditado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bloquear fechas por chat (Priority: P1)

El host le pide al agente cerrar la disponibilidad de una fecha o rango (p. ej. "cierra del 1 al 3 de julio" o "bloquea los fines de semana de agosto"). El agente PROPONE el bloqueo (mostrando cuántas noches y cuáles), el host CONFIRMA, y entonces esas noches quedan cerradas en la app y publicadas en Booking. Las noches con reserva ya existente se respetan (no se tocan) y se avisan.

**Why this priority**: Es la necesidad central y la que hoy falla (el agente proponía un precio por error). Sin esto, el host no puede cerrar fechas (mantenimiento, uso personal, etc.) desde la herramienta.

**Independent Test**: Pedir por chat cerrar un rango con noches libres; confirmar; verificar que esas noches quedan no disponibles en la app y en Booking, y que una noche reservada dentro del rango no se cierra.

**Acceptance Scenarios**:

1. **Given** un rango con noches disponibles, **When** el host pide bloquearlo y confirma, **Then** esas noches quedan cerradas (sin disponibilidad) en la app y publicadas en Booking.
2. **Given** un rango que incluye una noche con reserva confirmada, **When** el host pide bloquearlo, **Then** el sistema omite esa noche, cierra las demás y avisa cuáles se omitieron.
3. **Given** una propuesta de bloqueo, **When** el host NO confirma (cancela o cambia de tema), **Then** no se cierra ninguna noche.
4. **Given** que el host pide "quita la disponibilidad", **When** el agente responde, **Then** propone un BLOQUEO de disponibilidad (no un cambio de precio).

---

### User Story 2 - Reabrir fechas por chat (Priority: P1)

El host le pide al agente reabrir una fecha o rango previamente bloqueado (p. ej. "vuelve a abrir el 2 de julio"). El agente propone, el host confirma, y la disponibilidad se restaura en la app y en Booking.

**Why this priority**: Bloquear sin poder reabrir deja al host atrapado; abrir es la operación inversa imprescindible para que el bloqueo sea reversible y seguro.

**Independent Test**: Reabrir un rango que se había bloqueado; confirmar; verificar que vuelve a estar disponible en la app y en Booking.

**Acceptance Scenarios**:

1. **Given** un rango bloqueado, **When** el host pide reabrirlo y confirma, **Then** esas noches vuelven a estar disponibles en la app y en Booking.
2. **Given** una noche con reserva, **When** el host pide reabrir el rango, **Then** la reserva no se altera (la noche sigue ocupada por la reserva).

---

### User Story 3 - Bloquear/abrir desde el calendario (Priority: P2)

Desde el calendario de la web, el host selecciona un día o rango y elige "bloquear" o "abrir", ve una previsualización (cuántas noches, cuáles se omiten por reserva) y confirma. El calendario muestra visualmente las noches bloqueadas, reservadas, disponibles y sin datos.

**Why this priority**: Mejora la experiencia (gestión visual directa). Decidido en clarify: se INCLUYE en esta feature (no se difiere), junto con la gestión por chat.

**Independent Test**: Seleccionar un rango en el calendario, elegir bloquear, confirmar en el preview, y ver las noches marcadas como bloqueadas; repetir con "abrir".

**Acceptance Scenarios**:

1. **Given** una selección de días en el calendario, **When** el host elige bloquear y confirma el preview, **Then** esas noches se marcan como bloqueadas y se publican.
2. **Given** noches bloqueadas, reservadas, disponibles y sin datos, **When** el host ve el calendario, **Then** cada estado se distingue visualmente.

---

### Edge Cases

- **Noche reservada dentro del rango**: nunca se cierra ni se altera; se omite y se informa (no romper reservas → cero overbooking).
- **Publicación al Channel Manager falla**: el cambio local se conserva y se registra una incidencia; la operación no se cae (igual que en precios).
- **Bloquear algo ya bloqueado / abrir algo ya disponible**: operación idempotente; se informa que no hubo cambios.
- **Rango sin datos sincronizados** (fuera del horizonte): se puede bloquear/abrir igual (se crea el estado local y se publica), informando al host.
- **Cambio grande** (muchas noches): se refuerza el aviso antes de confirmar (coherente con el patrón de precios).
- **Filtro por días de semana** (p. ej. solo fines de semana): solo afecta los días que cumplen el filtro dentro del rango.
- **Reversibilidad**: todo bloqueo/apertura queda auditado y puede revertirse.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El host MUST poder bloquear (cerrar) la disponibilidad de una fecha o rango, con filtro opcional por días de semana.
- **FR-002**: El host MUST poder abrir (reabrir) la disponibilidad de una fecha o rango previamente bloqueado.
- **FR-003**: Todo cambio de disponibilidad MUST seguir el flujo humano-en-el-loop: el sistema PROPONE (con resumen de noches afectadas) y el host CONFIRMA antes de aplicar y publicar.
- **FR-004**: El sistema MUST publicar el cambio de disponibilidad al Channel Manager (cerrar = sin disponibilidad; abrir = disponibilidad restaurada al inventario de la unidad).
- **FR-005**: El sistema MUST NO cerrar ni alterar noches que ya tienen una reserva confirmada; esas noches se omiten y se informan al host.
- **FR-006**: Si la publicación al Channel Manager falla, el sistema MUST conservar el cambio local y registrar una incidencia, sin tumbar la operación.
- **FR-007**: Todo cambio de disponibilidad MUST quedar auditado (qué noches, antes/después, cuándo, origen: chat/manual). La reversión se realiza mediante la operación inversa ("abrir" deshace "bloquear" y viceversa); NO se expone un rollback puntual aparte.
- **FR-008**: El agente conversacional MUST disponer de capacidades para bloquear y abrir disponibilidad por rango, y MUST responder con claridad cuando se le pida disponibilidad (sin proponer cambios de precio en su lugar).
- **FR-009**: La previsualización de un bloqueo/apertura MUST indicar cuántas noches se afectan y cuáles se omiten (por reserva), antes de confirmar.
- **FR-010**: Tras confirmar, el estado de cada noche (disponible / bloqueada / reservada / sin datos) MUST reflejarse de forma consistente en la app.
- **FR-011** *(US3, incluido en esta feature)*: El calendario de la web MUST permitir seleccionar un día/rango y bloquear/abrir con previsualización y confirmación, distinguiendo visualmente los estados de cada noche (disponible / bloqueada / reservada / sin datos).

### Key Entities

- **Disponibilidad por noche**: estado de una noche de la unidad — disponible, bloqueada (cerrada por el host) o reservada (por una reserva); incluye el número de unidades disponibles.
- **Reserva**: ocupación confirmada de noches; es intocable por esta feature (define qué noches no pueden cerrarse ni alterarse).
- **Propuesta de cambio de disponibilidad**: cambio pendiente de confirmación (rango, acción bloquear/abrir, noches afectadas, noches omitidas), análogo a la propuesta de precio.
- **Registro de auditoría**: huella de cada cambio de disponibilidad (noches, antes/después, cuándo, origen) para trazabilidad y reversión.
- **Incidencia de publicación**: registro de un intento de publicación fallido al Channel Manager, para seguimiento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host puede cerrar un rango de noches libres por chat, con confirmación, en menos de 1 minuto, y verlas cerradas en la app y en Booking.
- **SC-002**: El 100% de las noches con reserva confirmada quedan intactas cuando se bloquea un rango que las contiene (cero reservas rotas).
- **SC-003**: El host puede reabrir un rango previamente bloqueado y verlo nuevamente disponible en la app y en Booking.
- **SC-004**: Ante una solicitud de disponibilidad, el agente nunca propone un cambio de precio; siempre propone (o explica) una acción de disponibilidad.
- **SC-005**: Si la publicación al Channel Manager falla, el cambio local persiste y queda registrada una incidencia consultable; ninguna operación termina en error para el host.
- **SC-006**: Todo cambio de disponibilidad queda auditado y es reversible (se puede deshacer y volver al estado anterior).

## Assumptions

- **Single-tenant, una unidad**: una sola propiedad/unidad; "disponibilidad" es a nivel de unidad y se comparte entre canales (cerrar una noche la cierra para Booking, único canal activo).
- **Inventario de la unidad**: "abrir" restaura la disponibilidad al inventario de la unidad (normalmente 1).
- **Reservas como fuente de verdad de ocupación**: las noches reservadas provienen de las reservas confirmadas ya importadas/sincronizadas.
- **Reutiliza el patrón existente**: el flujo propone→confirma→aplica→publica→audita ya existe para precios; esta feature lo extiende a disponibilidad (mismo mecanismo de confirmación, auditoría e incidencias).
- **Canal/escritura ya disponibles**: el conector del Channel Manager ya puede escribir disponibilidad por rango; esta feature lo usa.
- **US3 (calendario) incluido** (decidido en clarify): la gestión visual desde el calendario entra en esta feature, junto con el chat.
- **Reversibilidad por operación inversa** (decidido en clarify): "abrir" deshace "bloquear"; no hay rollback puntual aparte.
- **Fuera de alcance v1**: restricciones avanzadas (min/max stay, check-in/out por día), tarifas por canal, multi-unidad y multi-canal.
