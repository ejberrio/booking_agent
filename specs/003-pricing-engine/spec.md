# Feature Specification: Motor de precios

**Feature Branch**: `003-pricing-engine`  
**Created**: 2026-06-24  
**Status**: Draft  
**Input**: Capa de aplicación/API que permite al host consultar y gestionar precios y promociones (por día, rango y bloque, con preview y confirmación), apoyándose en el modelo de datos (001) y publicando los cambios a Beds24 vía el conector (002). Todo auditado y reversible. Single-tenant, COP, solo canal Booking.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar precios y calendario (Priority: P1)

El host consulta el precio de su unidad por día o por rango: ve el precio base, el precio efectivo (tras promociones), la disponibilidad y qué promociones aplican.

**Why this priority**: Antes de cambiar precios, el host necesita ver el estado actual. Es la base de toda gestión.

**Independent Test**: Consultar un día y un rango y obtener, por cada día, precio base, precio efectivo, disponibilidad y promociones vigentes.

**Acceptance Scenarios**:

1. **Given** una unidad con precio base y sin promociones, **When** se consulta un día, **Then** precio efectivo == precio base y se ve la disponibilidad.
2. **Given** una promoción vigente que cubre un día, **When** se consulta ese día, **Then** el precio efectivo refleja el descuento y se indica la promoción aplicada.
3. **Given** un rango de fechas, **When** se consulta, **Then** se obtiene el detalle por cada día del rango.

---

### User Story 2 - Asignar precio a un día específico (Priority: P1)

El host fija el precio de un día concreto; el sistema valida contra las reglas (min/max), audita el cambio y lo publica a Beds24.

**Why this priority**: Es la acción de escritura más básica y de mayor valor.

**Independent Test**: Fijar el precio de un día válido y confirmar que queda registrado en la auditoría y se publica al canal; intentar un precio fuera de límites y ver que se rechaza.

**Acceptance Scenarios**:

1. **Given** un precio dentro de los límites, **When** el host lo confirma para un día, **Then** el precio queda fijado, auditado (antes/después/origen) y publicado a Beds24.
2. **Given** un precio por debajo del mínimo (o sobre el máximo), **When** se intenta fijar, **Then** se rechaza con un mensaje claro y no se audita ni publica.
3. **Given** una publicación al canal que no se verifica, **When** se confirma el cambio, **Then** el cambio local se conserva y se reporta una incidencia de publicación.

---

### User Story 3 - Asignar precio por rangos con previsualización (Priority: P1)

El host fija un precio para un rango (semana, mes, rango arbitrario), pudiendo filtrar por días de la semana (p. ej. solo viernes y sábados) o por grupos de días. Antes de aplicar, ve una **previsualización (diff)** de qué días cambian y de qué valor a qué valor, y confirma explícitamente.

**Why this priority**: Es el caso de uso real del host (gestionar temporadas, fines de semana, meses) y donde el preview evita errores costosos.

**Independent Test**: Solicitar un cambio de rango filtrando por días de la semana, revisar el diff (días afectados y valores), confirmar y verificar que solo esos días cambiaron, quedaron auditados y publicados.

**Acceptance Scenarios**:

1. **Given** un rango y un precio, **When** el host solicita el cambio, **Then** recibe un diff con los días afectados y el valor anterior/nuevo de cada uno, SIN aplicar nada todavía.
2. **Given** un filtro por días de la semana, **When** se previsualiza, **Then** solo aparecen los días que cumplen el filtro.
3. **Given** un diff previsualizado, **When** el host confirma, **Then** se aplican exactamente esos cambios, cada uno auditado y publicado.
4. **Given** algún día del rango fuera de límites, **When** se previsualiza, **Then** esos días se señalan como inválidos y no se incluyen en la aplicación (o se bloquea la confirmación según la regla).

---

### User Story 4 - Gestionar promociones (Priority: P2)

El host crea, edita y elimina promociones (porcentaje o monto, vigencia, condiciones) y ve cómo afectan al precio efectivo. Si varias promociones cubren un día, aplica solo la de mayor descuento (no se acumulan).

**Why this priority**: Importante para el manejo comercial, pero se apoya en la consulta/aplicación de precios.

**Independent Test**: Crear una promoción para un rango, ver el efecto en el precio efectivo; crear otra solapada y verificar que gana la de mayor descuento; eliminarla y ver que el efectivo vuelve al base.

**Acceptance Scenarios**:

1. **Given** una promoción del 10% para un rango, **When** se crea, **Then** el precio efectivo de esos días baja un 10%.
2. **Given** dos promociones solapadas (10% y 20%), **When** se consulta un día cubierto, **Then** aplica solo la del 20% (no 30%).
3. **Given** una promoción existente, **When** se elimina, **Then** el precio efectivo de los días afectados vuelve al base.

---

### User Story 5 - Auditoría y rollback (Priority: P2)

El host consulta el historial de cambios de un día/rango (antes/después, cuándo, origen) y puede revertir un cambio. El rollback crea un nuevo cambio auditado; si hay cambios posteriores sobre la misma fecha, se señala conflicto y se pide confirmación.

**Why this priority**: Da confianza y control (principio III), pero se apoya en las escrituras anteriores.

**Independent Test**: Cambiar un precio, ver su entrada en el historial, revertirlo y comprobar que vuelve al valor anterior y se re-publica; provocar un conflicto y verificar que exige confirmación.

**Acceptance Scenarios**:

1. **Given** varios cambios sobre un día, **When** se consulta el historial, **Then** se ven en orden con valor anterior/nuevo y origen.
2. **Given** un cambio sin cambios posteriores, **When** el host lo revierte, **Then** el precio vuelve al valor anterior, se audita la reversión y se publica.
3. **Given** un cambio con cambios posteriores sobre la misma fecha, **When** se intenta revertir, **Then** se señala conflicto y se requiere confirmación explícita antes de aplicar.

---

### Edge Cases

- **Precio fuera de límites en una operación de rango**: los días inválidos se señalan; la confirmación no los aplica.
- **Publicación al canal no verificada**: el cambio local se conserva (auditado) y se reporta una incidencia; no se pierde el cambio.
- **Rango que cruza una promoción**: el preview muestra el precio base que se está fijando; el efectivo se recalcula con las promociones vigentes.
- **Confirmar un preview obsoleto**: si el estado cambió entre el preview y la confirmación, se detecta y se vuelve a previsualizar (no se aplica a ciegas).
- **Día sin precio previo**: fijarlo lo crea (valor anterior vacío en la auditoría).
- **Rollback de una creación (sin valor anterior)**: se maneja explícitamente (no se revierte a un precio nulo en silencio).
- **Promoción que dejaría el efectivo por debajo de 0**: el efectivo se acota a 0.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir consultar, por unidad y día/rango, el precio base, el precio efectivo (tras promociones), la disponibilidad y las promociones vigentes.
- **FR-002**: El sistema MUST permitir fijar el precio de un día específico.
- **FR-003**: El sistema MUST permitir fijar el precio de un rango (semana, mes, rango arbitrario), con filtro opcional por días de la semana y por grupos de días.
- **FR-004**: El sistema MUST generar una previsualización (diff) de un cambio de rango/bulk —días afectados con valor anterior y nuevo— SIN aplicar nada, y requerir confirmación explícita antes de escribir.
- **FR-005**: El sistema MUST validar cada precio contra las reglas de la propiedad (mínimo/máximo) y rechazar/señalar los que queden fuera de límites, sin auditar ni publicar esos.
- **FR-006**: El sistema MUST permitir crear, editar y eliminar promociones (porcentaje o monto, vigencia, condiciones) y reflejarlas en el precio efectivo.
- **FR-007**: El sistema MUST aplicar, cuando varias promociones cubren un día, únicamente la de mayor descuento (no se acumulan).
- **FR-008**: El sistema MUST auditar cada cambio de precio (valor anterior, nuevo, fecha/hora, origen) — reutilizando la auditoría existente — y MUST mantenerlo reversible.
- **FR-009**: El sistema MUST permitir revertir un cambio; la reversión crea un nuevo cambio auditado y, si existen cambios posteriores sobre la misma fecha, MUST señalar conflicto y requerir confirmación.
- **FR-010**: El sistema MUST publicar al Channel Manager (Beds24) cada cambio de precio confirmado (incluidas reversiones), reutilizando el conector; si la publicación no se verifica, MUST conservar el cambio local y reportar una incidencia.
- **FR-011**: El sistema MUST mostrar el historial de cambios de un día/rango (antes/después, cuándo, origen).
- **FR-012**: El sistema MUST tratar toda escritura de precio como una acción que requiere confirmación del host (human-in-the-loop), especialmente operaciones de rango/bulk.
- **FR-013**: El sistema MUST detectar un preview obsoleto (estado cambiado entre previsualizar y confirmar) y volver a previsualizar en lugar de aplicar a ciegas.
- **FR-014**: El alcance MUST limitarse al canal Booking activo y a la moneda de la propiedad (COP); single-tenant.

### Key Entities *(include if feature involves data)*

Reutiliza las entidades de la feature 001 (Rate, Promotion, PricingRule, PriceChangeLog, CalendarDay). Conceptos propios de esta feature:

- **Previsualización de cambio (ChangePreview)**: objeto transitorio (no persistido necesariamente) que describe un conjunto de cambios propuestos: lista de (día, valor anterior, valor nuevo, válido/ inválido + motivo) y un identificador/huella del estado base para detectar obsolescencia.
- **Selección de rango (RangeSelection)**: criterio de selección de días: rango de fechas + filtro opcional por días de la semana o grupos de días.
- **Resultado de aplicación (ApplyResult)**: resumen de un cambio aplicado: días cambiados, auditados, publicados y, en su caso, incidencias de publicación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host puede ver, para cualquier (día/rango), precio base, efectivo, disponibilidad y promociones, con un único resultado por día.
- **SC-002**: Toda escritura de precio confirmada queda auditada (antes/después/origen) y publicada a Beds24, o reporta incidencia si no se verifica — en el 100% de los casos.
- **SC-003**: Ninguna operación de rango/bulk se aplica sin una previsualización y una confirmación explícita (cero escrituras "a ciegas").
- **SC-004**: Un precio fuera de los límites de la propiedad nunca se aplica ni se publica (100%).
- **SC-005**: En promociones solapadas, el efectivo corresponde siempre a la de mayor descuento (nunca a la suma).
- **SC-006**: Cualquier cambio puede revertirse a su valor anterior; los conflictos (cambios posteriores) siempre exigen confirmación (cero sobrescrituras silenciosas).
- **SC-007**: Confirmar un preview obsoleto nunca aplica cambios incorrectos: el sistema vuelve a previsualizar.

## Assumptions

- **Reutiliza** la lógica de dominio (effective_price, best_promotion, violates_rule) y los servicios (pricing_service, audit_service) de la feature 001, y el conector/sync_service de la feature 002 para publicar.
- **Single-tenant**: un solo host; el "quién" de la auditoría se modela por origen (manual/chat/sugerencia), no por múltiples usuarios.
- **Moneda COP**; solo canal Booking activo (channel-aware; Airbnb inactivo).
- **Publicación en la confirmación**: al confirmar un cambio se audita y se publica; no hay un paso de publicación diferido separado en esta feature.
- **El preview no requiere persistencia**: puede ser un objeto transitorio; la obsolescencia se detecta con una huella del estado base.
- **Fuera de alcance**: UI/dashboard, agente conversacional, motor de sugerencias por eventos/mercado y gestión activa de otros canales.
