# Feature Specification: Ofertas de Booking.com (deals visibles)

**Feature Branch**: `009-booking-offers`
**Created**: 2026-06-28
**Status**: Draft
**Input**: User description: "Que el host pueda crear, ver, editar y finalizar las promociones NATIVAS de Booking.com (deals visibles con badge/descuento) desde el chat y desde un menú en la interfaz, publicadas vía el Channel Manager, con propone→confirma, auditoría y mensajes claros que las distingan de las promociones de precio internas."

## Clarifications

### Session 2026-06-28

- Q: ¿Qué tipos de oferta priorizamos en v1? → A: Última hora (Last-Minute) + Reserva anticipada (Early Booker) + Básica (Basic Deal, % por fechas) — sujeto a lo que la API permita crear (se confirma en el plan).
- Q: ¿Dónde vive el menú de ofertas? → A: Una sección dedicada "Ofertas" en el menú lateral (lista + formulario crear/editar/finalizar) Y un indicador/acción rápida en el calendario.
- Q: Si la API NO permite crear ofertas (solo leerlas), ¿qué hacemos en v1? → A: Mostrar las ofertas (lectura) y guiar/enlazar al extranet de Booking para crear/editar allí (degradación elegante, sin bloquear el valor de lectura).
- Q: (Hallazgo del PLAN, verificado en vivo) La API de Beds24 V2 **NO** gestiona los deals de Booking — ni crear ni listar (los deals se gestionan en el dashboard de Beds24 / extranet de Booking). ¿Alcance de v1? → A: **v1 ligera** — claridad del agente (explica que esos deals se gestionan en Beds24/Booking y enlaza, sin crear una promoción de precio interna por error) + una sección **"Ofertas"** en la web con la distinción y **deep-links** al dashboard/extranet. SIN creación/lectura por API ni indicador en calendario (no hay datos sincronizados). Detalle en `research.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Crear una oferta de Booking por chat (Priority: P1)

El host le pide al agente crear una oferta visible de Booking (p. ej. "crea una oferta Early Booker de 10% para septiembre" o "pon un descuento de última hora del 15%"). El agente PROPONE la oferta (tipo, descuento, fechas/condiciones), el host CONFIRMA, y la oferta se publica en Booking, donde aparecerá como deal con su etiqueta para los huéspedes.

**Why this priority**: Es la capacidad central que el host pidió y que hoy no existe (las "promociones" actuales solo bajan el precio, sin badge). Crear un deal visible es lo que mueve conversiones.

**Independent Test**: Pedir por chat crear una oferta soportada; confirmar; verificar que queda registrada como oferta activa de Booking (visible en el listado de ofertas) y reflejada en Booking.

**Acceptance Scenarios**:

1. **Given** ninguna oferta del tipo pedido, **When** el host pide crearla y confirma, **Then** la oferta queda activa/programada y publicada en Booking.
2. **Given** que el host pide "una promo que se VEA en Booking", **When** el agente responde, **Then** usa esta funcionalidad (oferta de Booking), no la promoción de precio interna.
3. **Given** una propuesta de oferta, **When** el host NO confirma, **Then** no se crea ninguna oferta.
4. **Given** un tipo de oferta no soportado o que Booking no permite crear por API (p. ej. Genius), **When** el host lo pide, **Then** el agente lo explica con claridad y no crea nada.

---

### User Story 2 - Gestionar ofertas desde la interfaz (Priority: P1)

Desde una **sección dedicada "Ofertas"** en el menú lateral, el host ve la lista de ofertas de Booking (tipo, descuento, fechas, estado), crea una nueva mediante un formulario (tipo, % descuento, fechas), y puede editar o finalizar (desactivar) una existente, con una previsualización y confirmación antes de publicar. El calendario incluye además un indicador y una acción rápida hacia esa sección.

**Why this priority**: Muchos hosts prefieren un formulario visual para configurar deals (elegir tipo, %, fechas) antes que describirlo por chat. Entrega el mismo valor con una UX directa.

**Independent Test**: Abrir el menú de ofertas, crear una con el formulario, confirmar el preview, verla en la lista como activa; luego finalizarla y verla como inactiva.

**Acceptance Scenarios**:

1. **Given** el menú de ofertas, **When** el host completa el formulario (tipo, descuento, fechas) y confirma, **Then** la oferta se crea y publica, y aparece en la lista.
2. **Given** una oferta activa, **When** el host la finaliza/desactiva y confirma, **Then** deja de estar activa en Booking y se refleja en la lista.
3. **Given** una oferta existente, **When** el host edita su descuento o fechas y confirma, **Then** se actualiza y republica.
4. **Given** datos inválidos en el formulario (p. ej. descuento fuera de rango o fechas incoherentes), **When** el host intenta guardar, **Then** se le indica el error y no se publica nada.

---

### User Story 3 - Ver el estado y distinguir tipos de descuento (Priority: P2)

El host entiende en todo momento qué descuentos tiene y de qué tipo. El calendario indica los días con una oferta de Booking activa, distinguible de una promoción de precio interna, de un bloqueo y de una reserva. La interfaz y el agente nombran cada cosa con claridad ("Ofertas de Booking" vs "Promociones de precio internas").

**Why this priority**: Evita confusión entre las dos clases de descuento (la nueva visible y la interna que solo baja el precio), que de otro modo llevaría a errores del host.

**Independent Test**: Con una oferta de Booking y una promoción de precio interna activas en fechas distintas, verificar que el calendario y los listados las muestran como cosas distinguibles y bien nombradas.

**Acceptance Scenarios**:

1. **Given** una oferta de Booking activa en un rango, **When** el host mira el calendario, **Then** esos días muestran un indicador propio de "oferta de Booking".
2. **Given** una oferta de Booking y una promoción de precio interna, **When** el host las consulta, **Then** se presentan con nombres y secciones diferenciadas (sin mezclarlas).

---

### Edge Cases

- **Tipo no creable por API** (p. ej. Genius): se informa y, si acaso, se muestra solo como lectura; no se intenta crear.
- **Publicación rechazada o fallida** (Booking/Channel Manager): se conserva el estado local conocido y se reporta una incidencia/mensaje claro; la operación no se cae.
- **Permisos insuficientes** (el acceso al Channel Manager no autoriza gestionar ofertas): se informa con un mensaje accionable (qué permiso falta) en vez de un error genérico.
- **Solapamiento** de varias ofertas en las mismas fechas: el sistema refleja lo que Booking permita; si Booking las rechaza o prioriza una, se informa.
- **Descuento fuera de rango** o fechas incoherentes (fin antes de inicio, ventana de reserva inválida para el tipo): se valida antes de publicar.
- **Finalizar una oferta ya finalizada / editar una inexistente**: operación idempotente; se informa que no hubo cambios.
- **Confusión con la promoción interna**: el host nunca debe terminar creando una cosa cuando pidió la otra; el agente confirma el tipo correcto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El host MUST poder ver la lista de ofertas de Booking de la propiedad (tipo, descuento, fechas/condiciones, estado), leídas del Channel Manager.
- **FR-002**: El host MUST poder crear una oferta de Booking de un tipo soportado (en v1: Última hora, Reserva anticipada y Básica), indicando descuento y fechas/condiciones, tanto por chat como por un formulario en una sección dedicada "Ofertas" de la interfaz.
- **FR-003**: El host MUST poder editar (descuento/fechas) y finalizar (desactivar) una oferta existente.
- **FR-004**: Toda creación/edición/finalización MUST seguir el flujo humano-en-el-loop: el sistema PROPONE/previsualiza y el host CONFIRMA antes de publicar.
- **FR-005**: El sistema MUST publicar la oferta al Channel Manager para que aparezca en Booking como deal visible.
- **FR-006**: Si la publicación falla o es rechazada, el sistema MUST conservar el estado local conocido y reportar una incidencia/mensaje claro, sin tumbar la operación.
- **FR-007**: Toda acción sobre ofertas MUST quedar auditada (qué, antes/después, cuándo, origen chat/interfaz) y ser reversible (una oferta creada puede finalizarse; una finalizada puede recrearse).
- **FR-008**: El sistema MUST distinguir claramente, en la interfaz y en el lenguaje del agente, las **Ofertas de Booking** (visibles, esta feature) de las **Promociones de precio internas** (que solo bajan el precio publicado).
- **FR-009**: El agente MUST elegir la funcionalidad correcta según la intención del host: si pide algo "que se vea en Booking" usa ofertas; si pide "bajar el precio" usa la promoción interna; ante ambigüedad, pregunta.
- **FR-010**: El calendario MUST indicar visualmente los días cubiertos por una oferta de Booking activa, distinguibles de promoción interna, bloqueo y reserva.
- **FR-011**: El sistema MUST validar los datos de la oferta (descuento dentro del rango permitido, fechas coherentes, condiciones válidas para el tipo) antes de publicar.
- **FR-012**: El sistema MUST indicar con claridad cuando un tipo de oferta no se puede gestionar por integración (p. ej. Genius), sin intentar crearlo.
- **FR-013**: Si el acceso al Channel Manager no autoriza gestionar ofertas, el sistema MUST informar qué permiso/credencial adicional se requiere (acción para el host), sin exponer secretos.
- **FR-014**: Si la integración NO permite CREAR/editar ofertas por API (solo leerlas), el sistema MUST degradar de forma elegante: mostrar las ofertas (lectura) y guiar/enlazar al extranet de Booking para crear/editar allí, sin bloquear el valor de lectura ni presentar un error genérico.

### Key Entities

- **Oferta de Booking**: un descuento visible publicado en Booking — tipo (p. ej. Básica, Última hora, Reserva anticipada), porcentaje de descuento, fechas de estancia y/o ventana de reserva según el tipo, nombre, estado (activa/programada/finalizada).
- **Tipo de oferta**: catálogo de tipos soportados (los creables por integración) y los no soportados/solo lectura (p. ej. Genius).
- **Propuesta de oferta**: cambio pendiente de confirmación (crear/editar/finalizar), análogo a las propuestas de precio/disponibilidad.
- **Registro de auditoría de ofertas**: huella de cada acción (qué oferta, antes/después, cuándo, origen) para trazabilidad y reversión.
- **Incidencia de publicación**: registro de un intento fallido/rechazado de publicar una oferta, para seguimiento.
- **Promoción de precio interna** *(existente, referida para distinción)*: descuento que solo baja el precio publicado; NO es una oferta visible de Booking.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host puede crear una oferta de Booking soportada (por chat o por el formulario), con confirmación, en menos de 2 minutos, y verla reflejada como oferta activa.
- **SC-002**: El host puede finalizar/desactivar una oferta y verla como inactiva, y volver a crearla si lo desea (reversible).
- **SC-003**: En el 100% de las solicitudes, el agente usa la funcionalidad correcta (oferta de Booking vs promoción interna) o pregunta ante ambigüedad; nunca crea una cuando se pidió la otra.
- **SC-004**: Si la publicación falla, el estado local se conserva y queda una incidencia/mensaje claro; ninguna operación termina en un error genérico para el host.
- **SC-005**: El host distingue sin ambigüedad, en la interfaz y el calendario, las ofertas de Booking de las promociones internas, los bloqueos y las reservas.
- **SC-006**: Toda acción sobre ofertas queda auditada y es reversible.

## Assumptions

- **Tipos soportados en v1** (decidido en clarify): Última hora (Last-Minute), Reserva anticipada (Early Booker) y Básica (Basic Deal, % por fechas). El conjunto efectivo queda sujeto a lo que el Channel Manager permita crear por API (se confirma en el plan).
- **Ubicación UI** (decidido en clarify): sección dedicada "Ofertas" en el menú lateral (lista + formulario) más un indicador/acción rápida en el calendario.
- **Plan B de creación** (decidido en clarify): si la API no permite crear/editar ofertas, v1 ofrece lectura de ofertas + enlace guiado al extranet de Booking (ver FR-014).
- **Genius fuera de alcance de creación**: Genius lo gestiona Booking y no se crea por integración; a lo sumo se muestra como lectura.
- **Permisos/credenciales**: gestionar ofertas puede requerir permisos adicionales en el acceso al Channel Manager; si así fuera, el host deberá habilitarlos/regenerar su credencial (acción del host, no del sistema).
- **Reutiliza el patrón existente**: propone→confirma→publica→audita ya existe para precios/disponibilidad; esta feature lo extiende a ofertas (mismo mecanismo de confirmación, auditoría e incidencias).
- **Single-tenant, un canal**: una propiedad/unidad, solo canal Booking, moneda COP.
- **Distinción de nombres**: "Ofertas de Booking" (visibles) vs "Promociones de precio internas" (bajan el precio) en toda la UI y el lenguaje del agente.
- **Fuera de alcance v1**: gestión de Genius (creación), multi-canal/multi-unidad, segmentación avanzada por país/dispositivo más allá de lo que el tipo de oferta implique, y analítica de rendimiento de las ofertas.
