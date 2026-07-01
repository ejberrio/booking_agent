# Feature Specification: Gestión de promociones de precio vía API

**Feature Branch**: `011-api-promotions`
**Created**: 2026-07-01
**Status**: Draft
**Input**: User description: gestionar promociones de precio (precio con descuento sobre un rango de fechas, ligado a una oferta existente) desde la app —por chat y calendario— con el patrón humano-en-el-bucle, aprovechando que el Channel Manager (Beds24 V2) SÍ permite crear/editar "fixed prices" por API (hallazgo verificado el 2026-07-01), a diferencia de lo asumido en la Feature 009.

## Clarifications

### Session 2026-07-01

- Q: ¿Cómo debe comportarse "retirar/quitar" una promoción, dado que la API no expone un borrado directo? → A: **Anular efecto + ocultar** — la app pone el precio de la promo igual/mayor al base para que deje de descontar y la oculta de las activas; efecto inmediato y reversible (posible registro neutralizado en el canal hasta limpieza manual eventual).
- Q: ¿Qué campos define una promoción además del precio y el rango de fechas (v1)? → A: **Precio + fechas + estancia mínima** propia opcional de la promo (el resto de reglas se heredan del contenedor de oferta).
- Q: Cuando el host pide un descuento en porcentaje, ¿qué guardamos? → A: **Guardar el % pedido y el precio absoluto** fijado; si cambia el base se avisa que el precio quedó fijo al crear.
- Q: ¿Sobre qué oferta se crea la promoción? → A: **Una oferta designada** en configuración ("oferta de promociones"); todas las promos v1 van a ese contenedor.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Crear una promoción con descuento para un rango de fechas (Priority: P1)

El host quiere ofrecer un precio rebajado durante unas fechas concretas (p. ej. "Vacaciones", del 15 al 31 de enero a 300.000 COP en vez del precio base). Lo pide por chat ("crea una promo del 15 al 31 de enero con 20% de descuento") o desde el calendario (selecciona el rango y elige "Crear promoción"). El sistema le muestra una **propuesta** clara (oferta elegida, fechas, precio actual → precio con descuento, % equivalente) y **solo tras su confirmación** la crea en el Channel Manager y la publica. Queda registrada para auditoría.

**Why this priority**: Es el núcleo de la feature y el mayor valor: poder lanzar ofertas reales sin entrar al panel de Beds24. Sin esto, la feature no existe. Además es el MVP autónomo (crear ya entrega valor aunque no exista editar/eliminar).

**Independent Test**: Pedir una promoción para un rango de fechas (por chat o calendario), verificar que la propuesta muestra fechas, oferta y precio con descuento coherentes con el precio base, confirmarla, y comprobar que queda creada en el Channel Manager y visible en la app.

**Acceptance Scenarios**:

1. **Given** la oferta de promociones designada y disponible, **When** el host pide una promoción para un rango de fechas indicando un descuento (en % o en precio absoluto) y opcionalmente una estancia mínima, **Then** el sistema calcula el precio con descuento a partir del precio base, muestra una propuesta (oferta, fechas, precio actual, precio propuesto, % equivalente, estancia mínima si aplica) y **no** aplica nada hasta la confirmación.
2. **Given** una propuesta de promoción mostrada, **When** el host la confirma, **Then** el sistema la crea/publica en el Channel Manager y confirma el resultado con las fechas y el precio aplicados.
3. **Given** una propuesta de promoción mostrada, **When** el host la rechaza o no confirma, **Then** no se crea ni publica nada.
4. **Given** un descuento pedido en porcentaje, **When** se genera la propuesta, **Then** el precio propuesto es el precio base menos ese porcentaje (redondeado de forma sensata) y nunca un valor ≤ 0.

---

### User Story 2 - Ver las promociones activas y su estado (Priority: P1)

El host quiere ver de un vistazo qué promociones tiene configuradas: nombre/oferta, rango de fechas, precio con descuento (y su ahorro frente al base), y si están publicadas correctamente o con incidencias. Lo consulta por chat ("¿qué promociones tengo?") y en la sección/vista de ofertas del calendario.

**Why this priority**: Sin visibilidad, el host no puede confiar en la herramienta ni decidir. Acompaña a US1 como parte del MVP: crear a ciegas no es aceptable; debe poder verificar el resultado.

**Independent Test**: Consultar las promociones (chat y UI) y verificar que la lista coincide con lo que existe en el Channel Manager (fechas, oferta, precio) y refleja incidencias de publicación si las hubiera.

**Acceptance Scenarios**:

1. **Given** una o más promociones existentes, **When** el host las consulta, **Then** ve por cada una: oferta, rango de fechas, precio con descuento, ahorro frente al base y estado de publicación.
2. **Given** ninguna promoción configurada, **When** el host consulta, **Then** ve un estado vacío claro con orientación de cómo crear una.
3. **Given** una promoción que falló al publicarse, **When** el host consulta, **Then** ve la incidencia señalada (no se muestra como sana).

---

### User Story 3 - Editar o retirar una promoción (Priority: P2)

El host quiere ajustar una promoción existente (cambiar fechas o precio) o retirarla antes de tiempo. Lo hace por chat ("sube la promo de enero a 320.000" / "quita la promo de enero") o desde la UI. Igual que en US1, se le muestra una propuesta del cambio y se aplica **solo tras confirmar**; el resultado se audita.

**Why this priority**: Completa el ciclo de vida, pero el valor esencial (lanzar una oferta) ya lo dan US1+US2. Editar/retirar es importante pero secundario para el primer incremento.

**Independent Test**: Sobre una promoción existente, pedir un cambio de fechas o precio y una retirada; verificar propuesta→confirmación→efecto en el Channel Manager, y que la auditoría registra ambos.

**Acceptance Scenarios**:

1. **Given** una promoción existente, **When** el host pide cambiar su precio o sus fechas, **Then** el sistema muestra la propuesta del cambio y, tras confirmar, la actualiza en el Channel Manager.
2. **Given** una promoción existente, **When** el host pide retirarla, **Then** el sistema explica cómo queda (deja de aplicar el descuento) y, tras confirmar, la retira/anula y lo refleja en la lista.
3. **Given** un cambio o retirada aplicados, **When** se consulta la auditoría, **Then** consta quién, cuándo y el antes/después.

---

### Edge Cases

- **Sin oferta designada**: si no está designada/creada la oferta de promociones (el contenedor se configura una sola vez en el panel del Channel Manager), el sistema lo explica y guía a configurarla allí, en lugar de fallar sin contexto.
- **Descuento inválido**: un % ≥ 100, un precio ≤ 0 o un precio por encima del base se rechazan con un mensaje claro (una "promoción" no puede encarecer ni regalar).
- **Rango de fechas inválido**: fin antes de inicio, fechas en el pasado, o rango vacío → mensaje claro, no se crea nada.
- **Solape con otra promoción** en las mismas fechas y oferta: el sistema advierte del solape y pide confirmación explícita antes de continuar.
- **Noches reservadas dentro del rango**: se informa que las reservas ya confirmadas no cambian de precio (la promo solo afecta nuevas reservas).
- **Límite del Channel Manager**: si se alcanza el máximo de promociones por habitación, el sistema lo comunica en lugar de fallar de forma opaca.
- **Fallo o lentitud al publicar**: si el Channel Manager no responde o rechaza, la promoción no se da por publicada; se registra una incidencia y el host la ve como pendiente/errónea, sin romper la app.
- **Cambio del precio base tras crear la promo**: la app muestra el ahorro con respecto al base vigente; si el descuento pactado fue en %, se documenta que el precio de la promo quedó fijado al crearla (no se recalcula solo).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir crear una promoción definida por: un rango de fechas (primera y última noche), un precio con descuento y, opcionalmente, una **estancia mínima** propia de la promo; por chat y por el calendario. La promoción se crea sobre la **oferta designada** (ver FR-014); el resto de reglas (cancelación, tipo de reserva, posición) se heredan de esa oferta.
- **FR-002**: El sistema MUST aceptar el descuento tanto en porcentaje como en precio absoluto, y en el caso de porcentaje MUST calcular el precio final a partir del precio base vigente para esas fechas. El sistema MUST **guardar tanto el % pedido como el precio absoluto** resultante; el precio queda fijado al crear la promo (no se recalcula solo si cambia el base) y, si el base cambia, MUST avisar de esa circunstancia.
- **FR-003**: El sistema MUST seguir el patrón humano-en-el-bucle: toda creación, edición o retirada MUST mostrarse primero como propuesta y aplicarse **solo tras confirmación** explícita del host (NON-NEGOTIABLE, alineado con la constitución).
- **FR-004**: La propuesta MUST mostrar, de forma comprensible, la oferta, el rango de fechas, el precio base de referencia, el precio con descuento y el ahorro (importe y % equivalente).
- **FR-005**: El sistema MUST validar y rechazar entradas inválidas: precio ≤ 0, precio ≥ precio base (no es descuento), % fuera de rango, rango de fechas inválido o en el pasado.
- **FR-006**: El sistema MUST publicar la promoción confirmada en el Channel Manager y MUST confirmar el resultado (fechas y precio aplicados).
- **FR-007**: El sistema MUST listar las promociones existentes con su oferta, fechas, precio con descuento, ahorro frente al base y estado de publicación; por chat y por la UI.
- **FR-008**: El sistema MUST permitir editar una promoción existente (fechas, precio y/o estancia mínima) y retirarla, ambos con propuesta→confirmación. La **retirada** se implementa **anulando el efecto** (fijando el precio de la promo igual o superior al base para que deje de descontar) y **ocultándola** de la lista de promociones activas; el efecto es inmediato y reversible (puede quedar un registro neutralizado en el canal hasta una eventual limpieza manual, que se documenta).
- **FR-009**: El sistema MUST registrar en auditoría cada creación, edición y retirada (quién, cuándo, antes/después), reutilizando el registro de acciones existente.
- **FR-010**: Ante un fallo de publicación, el sistema MUST registrar una incidencia y reflejar la promoción como no publicada/errónea, sin interrumpir el resto de la app (best-effort, resiliente), reutilizando el registro de incidencias existente.
- **FR-011**: El sistema MUST advertir de solapes con otras promociones en la misma oferta y fechas, y de noches ya reservadas dentro del rango, pidiendo confirmación antes de continuar.
- **FR-012**: El sistema MUST distinguir con claridad, para el host, entre "promoción de precio" (esta feature, gestionable por app) y "promoción/deal nativo de Booking.com" (Genius/Deals de la extranet, fuera de alcance v1), evitando dar por hecho que una se refleja como la otra.
- **FR-013**: El sistema MUST tratar el "contenedor de oferta" (sus reglas: activación, posición, estancia mínima, cancelación, nombre) como **solo lectura**: la app gestiona el precio/fechas de la promoción sobre una oferta existente, pero NO crea ni modifica ese contenedor (se configura una vez en el panel del Channel Manager).
- **FR-014**: El sistema MUST usar una **oferta designada por configuración** ("oferta de promociones") como contenedor de todas las promociones v1. Si esa oferta no está designada o no existe en el canal, el sistema MUST explicarlo y guiar al host a crearla/designarla, en lugar de fallar sin contexto.

### Key Entities *(include if feature involves data)*

- **Promoción de precio**: un precio con descuento aplicado a un rango de fechas (primera/última noche) sobre la oferta designada de una habitación. Atributos de dominio: oferta asociada (la designada), fechas, precio con descuento, precio base de referencia al crearla, **% de descuento pedido** (para mostrar/ahorro), **estancia mínima propia opcional**, estado de publicación, activa/retirada. Es lo que esta feature crea/edita/retira.
- **Oferta designada (contenedor)** *(existente, solo lectura por app)*: el "slot" —designado en configuración— sobre el que cuelgan todas las promociones v1, con sus reglas (activación, posición, estancia mínima por defecto, cancelación, nombre). Se configura en el panel del Channel Manager; la app solo lo lee para validar que existe y colgar las promociones.
- **Propuesta de promoción** *(patrón existente)*: representación previa a la confirmación (oferta, fechas, base, precio con descuento, ahorro) que el host aprueba o rechaza.
- **Registro de acción** *(existente, `AgentAction`)*: auditoría de cada creación/edición/retirada.
- **Incidencia de publicación** *(existente, `SyncIssue`)*: fallo al publicar la promoción al Channel Manager; alimenta el estado "no publicada/errónea".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host puede crear una promoción para un rango de fechas y verla aplicada en el Channel Manager en menos de 2 minutos, sin entrar al panel del Channel Manager.
- **SC-002**: El 100% de las creaciones/ediciones/retiradas pasan por una confirmación explícita antes de tener efecto (ninguna acción se aplica sin confirmar).
- **SC-003**: La lista de promociones de la app coincide con lo existente en el Channel Manager (oferta, fechas y precio) en el 100% de los casos verificados.
- **SC-004**: Ninguna entrada inválida (precio ≤ 0, ≥ base, % fuera de rango, fechas inválidas) llega a crear una promoción; todas se rechazan con un mensaje comprensible.
- **SC-005**: Un fallo de publicación nunca rompe la app: la promoción queda marcada como no publicada y con incidencia registrada en el 100% de esos casos.
- **SC-006**: Toda creación/edición/retirada queda auditada con antes/después (100%).

## Assumptions

- **Oferta designada pre-creada**: el host crea y designa una vez, en el panel del Channel Manager, **la oferta** ("de promociones") sobre la que colgarán todas las promociones (activación pública, nombre, reglas). La app no crea ese contenedor (es solo lectura por API); si no existe/está designada, la app guía a configurarlo.
- **Descuento: se guarda % y precio absoluto**: el host puede pedir un porcentaje, pero el sistema fija y envía un **precio absoluto** al canal (no hay campo de porcentaje) y **conserva el % pedido** para mostrar el ahorro. El precio queda fijado al crearla y no se recalcula solo si cambia el base (se avisa).
- **Reutiliza lo existente**: se apoya en el adaptador del Channel Manager ya en uso para precios/disponibilidad, en el patrón proponer→confirmar→aplicar→publicar, en la auditoría de acciones y en el registro de incidencias de publicación.
- **Alcance single-tenant**: un host, una propiedad/habitación principal; sin gestión multi-cliente.
- **Fuera de alcance v1**: crear/editar el contenedor de oferta por API; descuentos porcentuales automáticos del tipo early-booker/last-minute gestionados por reglas del canal; y la aparición como **promoción nativa de Booking.com** (Genius/Deals) en la extranet, que depende del mapeo de tarifas del canal y se documenta como salvedad a verificar, no como garantía.
- **Verificación de escritura controlada**: la validación de escritura real contra el Channel Manager se hará de forma acotada y reversible (o con limpieza manual documentada), dado que la API de escritura de promociones no expone un borrado directo.
