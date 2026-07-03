# Feature Specification: Sugerencias de precio en el calendario + acción única "Aprobar y aplicar"

**Feature Branch**: `014-calendar-suggestions`
**Created**: 2026-07-03
**Status**: Draft
**Input**: Issue #95 — Las sugerencias de precio del motor de inteligencia hoy viven solo en una lista (página Sugerencias y tarjeta del dashboard) y su ciclo exige dos pasos redundantes en single-tenant (aprobar solo marca; aplicar publica). El host quiere verlas en contexto — marcadas en el calendario en sus fechas — y resolverlas ahí mismo con una sola acción "Aprobar y aplicar" o "Rechazar". Decisión tomada el 2026-07-03: fusionar aprobar+aplicar en una sola acción.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resolver una sugerencia con una sola acción (Priority: P1)

Como host, quiero aprobar-y-aplicar (o rechazar) una sugerencia de precio con una sola acción tras ver su detalle completo, para no repetir el doble paso aprobar→aplicar que hoy no aporta nada siendo yo el único operador.

**Why this priority**: es la decisión ya tomada que motiva la feature; sin ella, el marcado en el calendario seguiría llevando a un flujo de dos pasos. Es además la única parte con escritura al canal (el corazón del cambio).

**Independent Test**: con una sugerencia vigente, ejecutar "Aprobar y aplicar" desde la lista existente y verificar que en una sola acción la sugerencia queda aplicada, el precio publicado y el cambio auditado; "Rechazar" la descarta como hoy.

**Acceptance Scenarios**:

1. **Given** una sugerencia vigente (propuesta), **When** el host ejecuta "Aprobar y aplicar", **Then** la sugerencia pasa a aplicada, el precio sugerido se publica al canal y el cambio queda auditado con enlace al registro de cambio de precio — todo como resultado de UNA sola acción.
2. **Given** una sugerencia vigente, **When** el host la rechaza, **Then** queda rechazada sin ningún cambio de precio (comportamiento actual intacto).
3. **Given** la publicación al canal falla, **When** el host ejecuta "Aprobar y aplicar", **Then** el sistema registra la incidencia, se lo comunica con un mensaje honesto y el estado local no miente (la sugerencia NO figura como aplicada si el precio no se publicó).
4. **Given** una sugerencia ya resuelta (aplicada o rechazada), **When** el host intenta resolverla de nuevo, **Then** el sistema lo rechaza con un mensaje claro que refleja el estado real.
5. **Given** el detalle presentado antes de la acción, **When** el host lo revisa, **Then** ve el efecto completo: precio sugerido vs precio actual, rango de fechas, confianza y racional — esa vista ES la previsualización informada del principio human-in-the-loop; nada se aplica sin ese clic explícito del host.

---

### User Story 2 - Ver las sugerencias en el calendario (Priority: P1)

Como host, quiero que los días cubiertos por una sugerencia vigente aparezcan marcados en el calendario con un estilo propio, para verlas en contexto (junto a precios, reservas, bloqueos y promociones) en lugar de tener que cruzar mentalmente la lista con las fechas.

**Why this priority**: es la otra mitad del issue: el contexto visual. Junto con la US1 forma el flujo completo "ver en contexto → resolver ahí mismo".

**Independent Test**: con una sugerencia vigente para un rango de fechas, abrir el calendario y verificar que exactamente esos días muestran el marcador de sugerencia, visualmente distinto de los marcadores existentes; los días sin sugerencia vigente no lo muestran.

**Acceptance Scenarios**:

1. **Given** una sugerencia vigente que cubre un rango de fechas, **When** el host abre el calendario, **Then** cada día del rango muestra un marcador de sugerencia distinguible de los marcadores de promoción, reserva y bloqueo existentes.
2. **Given** un día con sugerencia vigente Y promoción Y sin disponibilidad a la vez, **When** el host lo mira, **Then** los marcadores conviven (ninguno oculta al otro).
3. **Given** una sugerencia aplicada o rechazada, **When** el host abre el calendario, **Then** sus días NO muestran el marcador (solo las vigentes se marcan).
4. **Given** una sugerencia cuyo rango completo ya pasó (vencida), **When** el host abre el calendario, **Then** no se marca en días pasados ni genera ruido visual.

---

### User Story 3 - Resolver la sugerencia desde el calendario (Priority: P2)

Como host, quiero hacer clic en un día marcado y ver el detalle de la sugerencia (precio sugerido vs actual, rango, confianza, racional breve) con los botones "Aprobar y aplicar" y "Rechazar" ahí mismo, para cerrar el ciclo sin salir del calendario.

**Why this priority**: es la integración de US1+US2; depende de ambas. Vale por sí sola como mejora de flujo, pero el host ya puede resolver desde la lista.

**Independent Test**: hacer clic en un día marcado, verificar que el panel muestra el detalle completo de la sugerencia y que ambas acciones funcionan y refrescan el calendario y la lista.

**Acceptance Scenarios**:

1. **Given** un día con sugerencia vigente, **When** el host hace clic, **Then** ve el detalle: precio sugerido vs precio actual del día, rango de fechas completo de la sugerencia, confianza y racional breve, con las acciones "Aprobar y aplicar" y "Rechazar".
2. **Given** el detalle abierto, **When** el host ejecuta una acción, **Then** el resultado se comunica, y el calendario y la lista reflejan el nuevo estado (el marcador desaparece; si se aplicó, el precio del día se actualiza).
3. **Given** varias sugerencias vigentes que cubren el mismo día, **When** el host hace clic, **Then** ve todas las sugerencias de ese día y puede resolver cada una por separado.
4. **Given** una sugerencia resuelta por otra vía entre que se pintó el calendario y el clic (estado obsoleto), **When** el host intenta resolverla, **Then** recibe un mensaje honesto con el estado real y la vista se refresca (sin aplicar nada dos veces).
5. **Given** una sugerencia vigente cuyo rango ya empezó pero incluye días pasados, **When** el host la resuelve desde el calendario, **Then** el sistema aplica el precio solo hacia los días restantes o le comunica el efecto real antes de confirmar (nunca simula haber cambiado el pasado).

---

### User Story 4 - La lista sigue funcionando con el botón único (Priority: P2)

Como host, quiero que la página de Sugerencias existente conserve su función como vista alternativa, con el botón único "Aprobar y aplicar" en lugar de los dos botones actuales, para tener una vista de todas las sugerencias (incluida la historia) sin cambiar de hábitos.

**Why this priority**: continuidad y consistencia; evita que la misma sugerencia tenga dos semánticas distintas según la pantalla.

**Independent Test**: abrir la página de Sugerencias y verificar que cada sugerencia vigente ofrece exactamente dos acciones ("Aprobar y aplicar" / "Rechazar"), que funcionan igual que desde el calendario, y que la historia (aplicadas/rechazadas) se sigue viendo.

**Acceptance Scenarios**:

1. **Given** la página de Sugerencias, **When** el host la abre, **Then** cada sugerencia pendiente (propuesta o aprobada-sin-aplicar histórica) ofrece "Aprobar y aplicar" y "Rechazar" con su detalle completo, incluido el precio actual (ya no existe el paso intermedio "aprobar" sin aplicar).
2. **Given** sugerencias históricas aplicadas o rechazadas, **When** el host consulta el sistema, **Then** conservan su estado y su rastro de auditoría sin alteraciones (la lista muestra pendientes; la historia vive en la auditoría, como hoy).
3. **Given** el dashboard, **When** el host lo abre, **Then** la tarjeta de sugerencias recientes sigue funcionando como hoy.

---

### Edge Cases

- **Varias sugerencias vigentes sobre el mismo día**: el marcador indica que hay sugerencias; el detalle muestra todas y cada una se resuelve por separado.
- **Sugerencia vencida** (todo su rango en el pasado): no se marca en el calendario; si el host la intenta aplicar desde la lista, el sistema se lo advierte y no simula cambios sobre fechas pasadas.
- **Sugerencia parcialmente vencida** (el rango empezó, quedan días futuros): el sistema comunica el efecto real (solo días restantes) antes o al momento de la acción — nunca finge haber cambiado noches pasadas.
- **Estado obsoleto entre render y clic**: si la sugerencia fue resuelta por otra vía, la acción devuelve un mensaje honesto con el estado real y la vista se refresca; no hay doble aplicación.
- **Fallo de publicación al canal**: incidencia registrada y visible (patrón existente); la sugerencia no queda como aplicada si el precio no llegó al canal.
- **Sugerencias aprobadas-sin-aplicar preexistentes**: las que quedaron en el estado intermedio "aprobada" antes de esta feature deben seguir siendo resolubles (aplicarlas o rechazarlas) sin quedar huérfanas.
- **Convivencia de marcadores**: sugerencia + promoción + reserva/bloqueo en el mismo día se muestran sin ocultarse mutuamente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST ofrecer una acción única "Aprobar y aplicar" que, en una sola operación atómica, apruebe la sugerencia, aplique el precio sugerido y lo publique al canal, con la misma auditoría del flujo actual (enlace de la sugerencia al registro del cambio de precio).
- **FR-002**: La acción "Rechazar" MUST conservar su efecto actual (descarta sin ningún cambio de precio) y MUST aceptar tanto sugerencias propuestas como aprobadas-sin-aplicar históricas (para que ninguna quede huérfana).
- **FR-003**: Si la publicación al canal falla, el sistema MUST registrar una incidencia visible, comunicar el fallo con un mensaje claro y NO marcar la sugerencia como aplicada (el estado local refleja la realidad).
- **FR-004**: Antes de ejecutar "Aprobar y aplicar", el host MUST ver el detalle completo de la sugerencia (precio sugerido vs precio actual, rango de fechas, confianza, racional breve) EN AMBAS superficies (panel del calendario y tarjeta de la lista); esa vista constituye la previsualización informada del principio human-in-the-loop y ninguna escritura ocurre sin la acción explícita del host.
- **FR-005**: El calendario MUST marcar visualmente los días cubiertos por sugerencias vigentes, con un estilo distinguible de los marcadores existentes (promoción, reserva/disponibilidad, bloqueo) y conviviendo con ellos.
- **FR-006**: Solo las sugerencias vigentes (propuestas y con al menos un día no pasado) se marcan; aplicadas, rechazadas y vencidas no generan marcador.
- **FR-007**: Al hacer clic en un día marcado, el host MUST poder ver el detalle de TODAS las sugerencias vigentes de ese día y resolver cada una ("Aprobar y aplicar" / "Rechazar") sin salir del calendario.
- **FR-008**: Tras resolver una sugerencia, las vistas afectadas (calendario, lista, dashboard) MUST reflejar el nuevo estado sin pasos manuales.
- **FR-009**: Resolver una sugerencia ya resuelta (o resuelta concurrentemente por otra vía) MUST devolver un mensaje honesto con el estado real, sin aplicar cambios dos veces.
- **FR-010**: Una sugerencia con parte del rango en el pasado MUST aplicarse solo sobre los días restantes, comunicándolo; una totalmente vencida MUST rechazarse con aviso en lugar de simular efecto.
- **FR-011**: La página de Sugerencias existente MUST conservar su función mostrando TODAS las pendientes (propuestas y aprobadas-sin-aplicar históricas, para que estas últimas no queden invisibles e irresolubles) con la acción única; las aplicadas/rechazadas conservan su estado y auditoría.
- **FR-012**: El flujo del agente de chat y sus propuestas quedan intactos (fuera de alcance); ninguna respuesta existente cambia para quien no use las vistas nuevas.

### Key Entities

- **Sugerencia de precio (PriceSuggestion)**: ya existe (rango de fechas, precio sugerido, racional, confianza, estado). Gana una transición combinada propuesta→aplicada en una sola operación; no cambia su estructura.
- **Registro de cambio de precio**: ya existe; sigue siendo el destino del enlace de auditoría de la sugerencia aplicada.
- **Día del calendario (vista)**: gana la información derivada "sugerencias vigentes que cubren este día" (no persistida).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host resuelve una sugerencia (verla en contexto → decidir → aplicada o rechazada) en menos de 30 segundos y con una sola acción de confirmación, tanto desde el calendario como desde la lista.
- **SC-002**: El 100% de las sugerencias aplicadas por la acción única quedan auditadas con su enlace al registro de cambio y el precio publicado verificable en el canal.
- **SC-003**: El 100% de los días cubiertos por sugerencias vigentes — y solo esos — muestran el marcador en el calendario.
- **SC-004**: Cero dobles aplicaciones: resolver una sugerencia ya resuelta nunca produce un segundo cambio de precio.
- **SC-005**: Los 174 tests existentes siguen verdes; el comportamiento actual de rechazo, auditoría e historia no cambia.

## Assumptions

- Single-tenant: un solo host opera; la fusión aprobar+aplicar no elimina ningún control de cuatro-ojos porque nunca lo hubo.
- El detalle mostrado antes del clic (precio sugerido vs actual, rango, confianza, racional) es la previsualización informada exigida por el principio human-in-the-loop; la acción del host es la confirmación explícita.
- Los endpoints/acciones actuales de aprobar y aplicar por separado pueden mantenerse por compatibilidad o retirarse limpiamente — decisión del plan; la spec solo exige que la UI ofrezca únicamente la acción combinada y que nada histórico se rompa.
- "Vigente" = estado propuesto y con al menos un día del rango no pasado (hoy cuenta como no pasado).
- El racional mostrado es el existente (texto breve del motor actual); mejorar su explicabilidad es del issue #98.
- Fuera de alcance: mejora A/#94 (ofertas en el calendario), mejoras del motor (#98), flujo del agente de chat.
