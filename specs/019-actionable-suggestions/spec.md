# Feature Specification: Sugerencias accionables

**Feature Branch**: `019-actionable-suggestions`
**Created**: 2026-10-08
**Status**: Draft
**Input**: User description: "Sugerencias accionables (Feature 019): ocultar noches reservadas/bloqueadas en la pestaña Sugerencias, agrupar por evento/periodo, selección múltiple con una sola vista previa y confirmación, mantener sugerencias a la baja, refrescar el racional de las equivalentes."

## Contexto

La pestaña **Sugerencias** lista las propuestas de precio del motor (feature 018). Hoy casi todas cubren **un solo día**, así que aplicar los precios de un mes exige decenas de clics, cada uno con su propia vista previa y confirmación. Además, la lista muestra sugerencias para noches que **ya están reservadas** (el host no puede cambiar ese precio y le estorban), y una sugerencia que se conserva entre escaneos puede seguir mostrando una explicación vieja (p. ej. un dato de mercado que ya se descartó).

Decisiones del host (2026-10-08): agrupar **por evento/periodo**; **selección múltiple** con una sola vista previa y confirmación; **mantener las sugerencias a la baja** ("si no, la competencia me gana reservas"). En el **calendario** las sugerencias se siguen viendo como hoy (el host ve qué está reservado).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Solo veo lo que puedo vender (Priority: P1)

Como host, al abrir la pestaña Sugerencias quiero ver únicamente sugerencias para noches que **todavía puedo vender**. Si una noche ya está reservada o la bloqueé, su sugerencia no debe aparecer; y si la reserva se cancela o abro la fecha, la sugerencia debe volver a aparecer sola, sin esperar al escaneo del día siguiente.

**Why this priority**: es ruido que confunde y lleva a decisiones inútiles; además es la base sobre la que se agrupa y se aplica en lote (no tiene sentido agrupar noches que no se pueden vender).

**Independent Test**: con una sugerencia del 9–13 de octubre y una reserva confirmada del 9 al 12, la pestaña muestra solo la noche del 12 (la del 13 si está libre); al cancelar la reserva y sincronizar, vuelven a aparecer las noches 9–11 sin correr el escaneo.

**Acceptance Scenarios**:

1. **Given** una sugerencia cuyas noches están todas reservadas, **When** el host abre la pestaña Sugerencias, **Then** esa sugerencia no aparece.
2. **Given** una sugerencia de 5 noches con 2 reservadas, **When** el host abre la pestaña, **Then** la sugerencia aparece solo con las 3 noches libres y así lo indica (p. ej. "3 de 5 noches; 2 ya reservadas").
3. **Given** una noche bloqueada manualmente por el host, **When** abre la pestaña, **Then** su sugerencia tampoco aparece.
4. **Given** una sugerencia oculta por una reserva, **When** la reserva se cancela y la app sincroniza (cron, botón o chat), **Then** la sugerencia vuelve a aparecer en la pestaña sin necesidad de un nuevo escaneo.
5. **Given** las mismas sugerencias, **When** el host mira el calendario, **Then** los marcadores de sugerencia se ven igual que hoy (sin cambios en el calendario).

---

### User Story 2 - Aplicar varias de una vez (Priority: P1)

Como host quiero **marcar varias sugerencias** y aplicarlas juntas: revisar en **una sola vista previa** qué precio queda en cada noche (antes → después) y **confirmar una vez**. Al terminar quiero ver qué noches se aplicaron y cuáles se omitieron y por qué.

**Why this priority**: es el dolor principal ("aplicar día a día es lento"); reduce decenas de confirmaciones a una, sin perder el control humano.

**Independent Test**: marcar 6 sugerencias de días distintos, abrir la vista previa (una tabla con 6+ noches, precio actual y nuevo), confirmar, y verificar que los precios quedaron publicados en el canal y que el resultado lista las noches aplicadas y omitidas.

**Acceptance Scenarios**:

1. **Given** varias sugerencias marcadas, **When** el host pide aplicar, **Then** ve una única vista previa con cada noche afectada, su precio actual y el nuevo, y el total de noches.
2. **Given** la vista previa abierta, **When** el host confirma, **Then** se aplican y publican todas las noches válidas con una sola confirmación, y cada sugerencia queda como aplicada.
3. **Given** la vista previa abierta, **When** entre la vista previa y la confirmación cambia algo relevante (otra persona/proceso cambió un precio, entró una reserva), **Then** la confirmación se rechaza con un mensaje claro y se pide revisar de nuevo (nada se publica a medias sin revisión).
4. **Given** una selección donde una noche ya no es aplicable (p. ej. se reservó), **When** se muestra la vista previa, **Then** esa noche aparece como omitida con su motivo y el resto sigue siendo aplicable.
5. **Given** la publicación al canal falla para algunas noches, **When** termina la aplicación, **Then** el resultado lo dice honestamente por noche y esas sugerencias no quedan marcadas como aplicadas.
6. **Given** el host no marca nada, **When** mira la pestaña, **Then** el botón de aplicar selección no está disponible.

---

### User Story 3 - Bloques por evento o periodo (Priority: P2)

Como host quiero ver las sugerencias **agrupadas en bloques** por evento o por días seguidos (p. ej. "Juanes · 14–16 nov", "Semana libre · 20–22 oct"), con el precio por noche visible, para entender y aplicar un bloque completo de un clic (que entra en la misma selección múltiple).

**Why this priority**: multiplica la agilidad de la historia 2 y da contexto (por qué ese precio), pero la historia 2 ya funciona sin agrupar.

**Independent Test**: con sugerencias de un día para el 14, 15 y 16 de noviembre por el mismo evento, la pestaña muestra un solo bloque "Juanes · 14–16 nov" con el precio de cada noche; marcar el bloque selecciona sus 3 noches.

**Acceptance Scenarios**:

1. **Given** sugerencias del mismo evento en días distintos (seguidos o no), **When** el host abre la pestaña, **Then** aparecen en un único bloque con el nombre del evento y su rango de fechas.
2. **Given** sugerencias de días seguidos sin evento y con la misma razón (p. ej. "libre próximo"), **When** abre la pestaña, **Then** se agrupan en un bloque de periodo.
3. **Given** un bloque con precios distintos por noche, **When** el host lo expande, **Then** ve el precio sugerido de cada noche y su variación frente al actual (sube/baja).
4. **Given** un bloque, **When** el host lo marca, **Then** quedan seleccionadas todas sus noches visibles; puede desmarcar sugerencias individuales del bloque.
5. **Given** bloques a la baja y al alza, **When** se listan, **Then** ambos se muestran por igual (las bajadas no se filtran ni se esconden).

---

### User Story 4 - Explicación siempre al día (Priority: P3)

Como host quiero que la explicación de cada sugerencia refleje **el último escaneo**: si una sugerencia se conserva porque el precio sugerido no cambió, su explicación (eventos, mercado, ocupación) debe actualizarse.

**Why this priority**: evita confusiones (p. ej. ver un dato de mercado ya descartado), pero no bloquea la operación.

**Independent Test**: una sugerencia pendiente cuyo precio se repite en el siguiente escaneo con una explicación distinta muestra la explicación nueva, sin duplicarse ni cambiar de estado.

**Acceptance Scenarios**:

1. **Given** una sugerencia pendiente equivalente (mismas fechas y precio) en el nuevo escaneo, **When** termina el escaneo, **Then** conserva su identidad y estado, pero su explicación y confianza son las del último escaneo.
2. **Given** una sugerencia ya aplicada o rechazada, **When** hay un escaneo, **Then** su explicación no cambia (queda como registro histórico).

---

### Edge Cases

- Sugerencia que cruza el día de hoy: las noches pasadas no se muestran ni se aplican.
- Noche con reserva que termina ese día (día de salida): la noche **es vendible** (el día de salida no ocupa).
- Dos sugerencias pendientes que pidan precios distintos para la misma noche: no debería ocurrir (el motor nunca deja dos pendientes por noche); si ocurriera, la selección no permite aplicar ambas y la vista previa lo marca como conflicto.
- Selección muy grande (p. ej. 60 noches): la vista previa sigue siendo legible (resumen + detalle) y la aplicación se completa en una sola confirmación.
- Precio sugerido fuera de los límites vigentes (piso/techo de la regla cambiados después del escaneo): la noche se omite con motivo "fuera de límites".
- Sin sugerencias vendibles: la pestaña lo dice claramente ("No hay sugerencias para noches libres") en vez de quedar vacía.
- El host aplica desde la pestaña mientras el escaneo diario corre: la confirmación con datos desactualizados se rechaza (escenario 2.3).

## Requirements *(mandatory)*

### Functional Requirements

**Visibilidad (US1)**

- **FR-001**: La pestaña Sugerencias MUST mostrar solo las noches **vendibles** de cada sugerencia pendiente: futuras (desde hoy), sin reserva confirmada y sin bloqueo manual.
- **FR-002**: Una sugerencia sin noches vendibles MUST NOT aparecer en la pestaña; una con algunas MUST mostrar cuántas de sus noches son vendibles y cuántas están ocupadas.
- **FR-003**: La visibilidad MUST evaluarse con el estado de ocupación vigente **al momento de consultar** (reservas y bloqueos ya sincronizados), de modo que una cancelación o apertura haga reaparecer la sugerencia sin esperar un escaneo.
- **FR-004**: El calendario MUST seguir mostrando los marcadores de sugerencia como hoy (sin filtrar por ocupación).

**Aplicación en lote (US2)**

- **FR-005**: El host MUST poder seleccionar varias sugerencias (y/o bloques) y pedir su aplicación conjunta.
- **FR-006**: Antes de publicar, el sistema MUST presentar **una única vista previa** con cada noche afectada: fecha, precio actual, precio nuevo, sugerencia de origen y, si aplica, motivo de omisión.
- **FR-007**: La aplicación MUST requerir **una confirmación explícita** sobre esa vista previa; la confirmación MUST rechazarse si el estado relevante (precios, ocupación, límites o las sugerencias seleccionadas) cambió desde la vista previa.
- **FR-008**: Las noches no aplicables (ocupadas, pasadas, fuera de límites, sugerencia ya resuelta) MUST omitirse con su motivo, sin impedir aplicar el resto.
- **FR-009**: Tras confirmar, el sistema MUST publicar al canal las noches válidas, registrar cada cambio en la auditoría con su sugerencia de origen y marcar como aplicadas **solo** las sugerencias cuyas noches se publicaron correctamente.
- **FR-010**: El resultado MUST informar por noche qué se aplicó, qué se omitió y qué falló al publicar, con mensajes en español claros.
- **FR-011**: Los límites del motor (piso y techo de la regla de precios) MUST respetarse en la vista previa y en la aplicación.

**Agrupación (US3)**

- **FR-012**: La pestaña MUST agrupar sugerencias vendibles en **bloques**: (a) por evento, uniendo todas las del mismo evento; (b) por periodo, uniendo días seguidos con la misma razón principal (ocupación, hueco libre).
- **FR-013**: Cada bloque MUST mostrar su nombre (evento o tipo de periodo), rango de fechas, número de noches, y el precio sugerido por noche con su variación frente al actual (sube/baja).
- **FR-014**: Marcar un bloque MUST seleccionar todas sus noches vendibles; el host MUST poder desmarcar sugerencias individuales dentro del bloque.
- **FR-015**: Las sugerencias **a la baja** MUST mostrarse y poder aplicarse igual que las al alza.

**Racional (US4)**

- **FR-016**: Cuando un escaneo conserva una sugerencia pendiente equivalente, MUST actualizar su explicación y confianza con las del último escaneo, sin cambiar su identidad ni su estado.
- **FR-017**: Las sugerencias aplicadas o rechazadas MUST conservar su explicación original.

**Compatibilidad**

- **FR-018**: Aplicar o rechazar una sugerencia individual (flujo actual) MUST seguir funcionando igual.
- **FR-019**: Nada se publica al canal sin la confirmación explícita del host (Principio III).

### Key Entities

- **Sugerencia de precio** (existente): rango de noches, precio sugerido, explicación (factores: evento, ocupación, hueco libre, mercado), confianza y estado (pendiente, aplicada, rechazada, reemplazada).
- **Noche vendible** (derivada): noche futura de una sugerencia pendiente sin reserva confirmada ni bloqueo; no se almacena, se calcula al consultar.
- **Bloque** (derivado, de presentación): conjunto de sugerencias vendibles agrupadas por evento o por periodo contiguo con la misma razón.
- **Aplicación en lote**: vista previa (lista de noches con antes/después y omisiones, más una huella del estado revisado) y su resultado por noche; cada noche aplicada queda en la auditoría enlazada a su sugerencia.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Aplicar las sugerencias de un mes completo (≈ 20–30 noches) requiere **una** vista previa y **una** confirmación, frente a una por sugerencia hoy.
- **SC-002**: El 100 % de las noches reservadas o bloqueadas quedan fuera de la pestaña Sugerencias; al cancelarse una reserva, sus noches vuelven a la pestaña en la siguiente consulta tras sincronizar (sin escaneo).
- **SC-003**: El host identifica de qué evento o periodo viene cada precio sin abrir el detalle: cada bloque muestra nombre, fechas y precios por noche.
- **SC-004**: 0 publicaciones al canal sin confirmación explícita; 0 sugerencias marcadas como aplicadas cuyas noches no se publicaron.
- **SC-005**: Las sugerencias a la baja aparecen en la pestaña en la misma proporción en que el motor las genera (no se filtran).
- **SC-006**: Ninguna sugerencia pendiente muestra una explicación más antigua que el último escaneo.

## Assumptions

- La ocupación (reservas confirmadas y bloqueos) es la ya sincronizada en la app (cron diario, botón Sincronizar o chat); la vigencia en tiempo real depende de la sincronización (los webhooks son el issue #117, fuera de alcance).
- El precio que se publica es el **precio sugerido** de cada noche, tal cual (editar el precio antes de aplicar queda fuera de alcance por decisión del host).
- Rechazar en bloque y "aplicar todo" quedan fuera de alcance por ahora.
- Single-tenant: un host, una propiedad, una unidad.
- Los marcadores del calendario y su panel de sugerencias por día se mantienen sin cambios.
- La agrupación es de presentación: no cambia cómo el motor genera ni almacena las sugerencias.
