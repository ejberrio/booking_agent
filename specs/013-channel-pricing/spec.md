# Feature Specification: Precios y promociones por canal (Booking.com + Airbnb)

**Feature Branch**: `013-channel-pricing`
**Created**: 2026-07-02
**Status**: Draft
**Input**: Issue #88 — Tras la Feature 012 la app distingue canales, pero el precio es uno solo para todos y las promociones de precio aplican a todos los canales a la vez. El host necesita control y visibilidad del precio por canal: definir un recargo/descuento porcentual por canal (p. ej. compensar el margen cambiario de Airbnb), ver el precio efectivo que percibe el huésped de cada canal, conocer (y si es posible limitar) el alcance por canal de sus promociones, y acceso directo a los deals nativos de Airbnb.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ajuste de precio por canal (Priority: P1)

Como host, quiero definir un ajuste porcentual por canal (p. ej. "Airbnb +8%", "Booking 0%") revisando una propuesta antes de confirmar, para controlar cuánto se cobra en cada canal sin cambiar mi precio base — y poder volver a 0% cuando quiera.

**Why this priority**: es el control central que da nombre a la feature. Hoy el precio de Airbnb depende de una conversión configurada fuera de la app, invisible y no gestionable desde ella.

**Independent Test**: configurar +8% para Airbnb vía la app (previsualización → confirmación), verificar que el ajuste queda registrado y auditado, que el precio efectivo del canal lo refleja, y que ponerlo de nuevo en 0% restaura el comportamiento anterior.

**Acceptance Scenarios**:

1. **Given** ningún ajuste configurado (comportamiento actual), **When** el host consulta el ajuste por canal, **Then** ve 0%/ninguno para todos los canales y el precio efectivo es igual al base.
2. **Given** el host pide "Airbnb +8%", **When** el sistema presenta la propuesta, **Then** muestra el efecto con un ejemplo concreto (precio base → precio efectivo del canal) y NO aplica nada hasta confirmación explícita.
3. **Given** una propuesta de ajuste confirmada, **When** se aplica, **Then** queda auditada (quién, cuándo, antes/después) y es reversible (volver al valor anterior es una operación equivalente).
4. **Given** un ajuste aplicado, **When** el host publica un precio nuevo o cambia el precio base, **Then** el canal ajustado sigue reflejando base + ajuste sin pasos manuales adicionales.
5. **Given** un ajuste fuera de rango razonable (p. ej. −100% o +500%), **When** el host lo propone, **Then** el sistema lo rechaza con un mensaje claro.

---

### User Story 2 - Ver el precio efectivo por canal (Priority: P2)

Como host, quiero ver en la app qué precio percibe el huésped de cada canal (base + ajuste del canal), para no tener que entrar a Booking y a Airbnb a comprobarlo.

**Why this priority**: sin visibilidad, el ajuste (US1) es una caja negra; juntos cierran el ciclo control+verificación.

**Independent Test**: con un ajuste configurado, consultar el calendario/estado y ver por fecha el precio base y el efectivo por canal; con ajuste 0%, ambos coinciden.

**Acceptance Scenarios**:

1. **Given** un ajuste "Airbnb +8%" activo y precio base 300.000, **When** el host consulta un día en la app, **Then** ve el base (300.000) y el efectivo de Airbnb (324.000) identificados por canal.
2. **Given** el host pregunta al agente "¿a cuánto está la noche del 15 en cada canal?", **When** el agente responde, **Then** informa el precio por canal usando el ajuste vigente.
3. **Given** el agente propone un cambio de precio, **When** presenta la propuesta, **Then** menciona el efecto por canal si hay ajustes distintos de 0% (p. ej. "300.000 en Booking, ~324.000 en Airbnb con tu +8%").

---

### User Story 3 - Promociones con alcance de canal (Priority: P2)

Como host, quiero que al crear o listar una promoción de precio quede claro a qué canales afecta y, si la plataforma lo permite, elegir su alcance (p. ej. solo Booking), además de una advertencia si puede duplicarse con un deal nativo activo en las mismas fechas.

**Why this priority**: evita el error caro ya vivido (doble descuento con el deal de julio): el host debe saber SIEMPRE el alcance de un descuento antes de confirmar.

**Independent Test**: crear una promoción y verificar que el preview y la lista muestran su alcance de canales; si el alcance elegible está disponible, crear una limitada a un canal y verificar que el otro canal no la refleja.

**Acceptance Scenarios**:

1. **Given** el host crea una promoción de precio, **When** ve la propuesta, **Then** esta indica explícitamente a qué canales afectará antes de confirmar.
2. **Given** la plataforma permite limitar el alcance, **When** el host elige "solo Booking", **Then** la promoción se publica afectando solo ese canal y la lista la muestra con su alcance.
3. **Given** la plataforma NO permite limitar el alcance, **When** el host intenta elegir un canal, **Then** el sistema se lo comunica ("las promociones de precio aplican a todos los canales") en lugar de fingir que lo hizo.
4. **Given** el host confirma una promoción para fechas donde él registró/conoce un deal nativo activo, **When** ve la propuesta, **Then** incluye la advertencia de posible doble descuento (patrón existente).

---

### User Story 4 - Acceso directo a los deals nativos de Airbnb (Priority: P3)

Como host, quiero enlaces directos desde la sección Ofertas a los descuentos/promociones nativos de Airbnb (semanal, mensual, promociones del anuncio) y a su página en el canal manager, con una guía de qué se gestiona dónde — como ya existe para Booking.

**Why this priority**: completa la paridad con Booking (PR #85); es navegación/documentación, sin lógica nueva.

**Independent Test**: abrir la sección Ofertas y verificar los enlaces de Airbnb (llevan a las páginas correctas) y el texto guía actualizado a dos canales.

**Acceptance Scenarios**:

1. **Given** la sección Ofertas, **When** el host la abre, **Then** ve enlaces directos a los deals nativos de Airbnb además de los de Booking, con guía de qué se gestiona en cada sitio.
2. **Given** la guía, **When** el host la lee, **Then** distingue: promociones de precio (app, con su alcance), deals con badge de Booking (panel Booking/Beds24) y descuentos/promos de Airbnb (Airbnb).

---

### Edge Cases

- **Ajuste sobre el mecanismo cambiario existente**: el canal Airbnb ya lleva una conversión de moneda en el canal manager; el ajuste por canal debe componerse con ella sin romperla (definir en diseño si el ajuste reemplaza, multiplica o se declara sobre esa conversión) y el precio efectivo mostrado debe reflejar el resultado final.
- **Ajuste sobre canal inactivo**: configurar ajuste para un canal desactivado se permite pero se señala (no tendrá efecto hasta reactivarlo).
- **Promociones existentes al cambiar el ajuste**: una promoción activa (precio absoluto) no se recalcula al cambiar el ajuste del canal; la lista debe dejar claro el efecto por canal vigente.
- **Fallo al materializar el ajuste en el canal manager**: si la aplicación del ajuste falla aguas abajo, el host ve una incidencia (patrón de incidencias de sincronización existente) y el estado local no miente (no marca aplicado lo no aplicado).
- **Redondeos**: los precios efectivos por canal se muestran redondeados de forma consistente y documentada (los canales no aceptan decimales arbitrarios en COP).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El host MUST poder consultar el ajuste porcentual vigente por canal (default 0%/ninguno = comportamiento actual intacto).
- **FR-002**: El host MUST poder proponer un ajuste porcentual por canal y el sistema MUST presentar una previsualización con ejemplo concreto ANTES de aplicar nada (human-in-the-loop, no negociable).
- **FR-003**: La aplicación de un ajuste MUST quedar auditada (quién, cuándo, antes/después, origen) y MUST ser reversible.
- **FR-004**: El sistema MUST validar el rango del ajuste (límites razonables definidos en diseño; nunca precios ≤ 0) y rechazar valores fuera de rango con mensaje claro.
- **FR-005**: El sistema MUST mostrar el precio efectivo por canal (base + ajuste, componiendo cualquier mecanismo cambiario existente del canal) en la consulta de calendario/precios.
- **FR-006**: El agente MUST informar el precio por canal cuando el host lo pida y MUST mencionar el efecto por canal en sus propuestas de precio cuando exista un ajuste distinto de 0%.
- **FR-007**: El preview y la lista de promociones de precio MUST indicar el alcance de canales de cada promoción.
- **FR-008**: Si la plataforma permite limitar una promoción a ciertos canales, el host MUST poder elegir el alcance al crearla; si no lo permite, el sistema MUST comunicarlo en lugar de simularlo (la decisión de si es posible es parte del diseño/investigación).
- **FR-009**: La propuesta de promoción MUST mantener la advertencia de posible doble descuento con deals nativos (patrón existente), ahora consciente de ambos canales.
- **FR-010**: La sección Ofertas MUST incluir enlaces directos a los deals nativos de Airbnb y guía de qué se gestiona dónde, en paridad con lo existente para Booking.
- **FR-011**: Un fallo al materializar el ajuste en el canal manager MUST registrarse como incidencia visible y el estado local MUST reflejar la realidad (no "aplicado" si no se aplicó).
- **FR-012**: Sin configuración nueva, el comportamiento actual MUST permanecer idéntico (ajustes en 0%/ninguno; publicación de precios y promociones como hoy).

### Key Entities

- **Canal (Channel)**: ya existe; su atributo de ajuste porcentual de precio (hoy sin uso) pasa a ser gestionable y auditable.
- **Promoción**: ya existe; gana visibilidad (y si es posible, control) de su alcance por canales.
- **Precio efectivo por canal**: vista derivada (no persistida): precio base del día + ajuste del canal + mecanismo cambiario del canal.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host configura un ajuste por canal (propuesta → confirmación) en menos de 1 minuto desde la app o el chat, y el cambio queda auditado el 100% de las veces.
- **SC-002**: Con un ajuste activo, el precio efectivo por canal mostrado en la app coincide con el publicado en el canal (verificación en vivo sobre el anuncio real, tolerancia de redondeo documentada).
- **SC-003**: El 100% de las propuestas de promoción muestran su alcance de canales antes de confirmar.
- **SC-004**: Con ajustes en 0%/ninguno, la salida de precios y promociones es byte-a-byte equivalente al comportamiento pre-feature (los 129 tests existentes siguen verdes sin modificaciones de expectativas de precio).
- **SC-005**: El host llega a los deals nativos de Airbnb desde la sección Ofertas en un clic.

## Assumptions

- Single-tenant; el canal manager (Beds24) sigue siendo la vía única de publicación.
- El **cómo** se materializa el ajuste en el canal manager (multiplicador del mapping, slots de precio por canal u otro mecanismo) es una decisión de investigación del plan; la spec solo exige el efecto observable (precio efectivo correcto en el canal) y la resiliencia (FR-011).
- La posibilidad de limitar promociones por canal depende de capacidades de la plataforma (campos de gestión de canal del canal manager); la spec exige honestidad del sistema en ambos resultados (FR-008).
- Los deals nativos (Booking y Airbnb) siguen gestionándose fuera de la app (sin API); esta feature solo enlaza y guía.
- El principio human-in-the-loop aplica a TODA escritura nueva (ajustes y promociones con alcance).
- Fuera de alcance: scan de mercado Airbnb (#89), sync de estados de reservas (#91), gestión de deals nativos por API.
