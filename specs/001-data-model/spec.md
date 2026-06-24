# Feature Specification: Modelo de datos del dominio

**Feature Branch**: `001-data-model`  
**Created**: 2026-06-24  
**Status**: Draft  
**Input**: Modelo de datos del dominio para Booking AI Agent (single-tenant, herramienta personal de un host): entidades, atributos clave y relaciones que sostienen la gestión de precios, promociones, sugerencias, auditoría y chat. Arquitectura channel-aware con solo Booking.com activo.

## Clarifications

### Session 2026-06-24

- Q: Cuando varias promociones se solapan en un mismo día, ¿cómo se resuelve el precio efectivo? → A: Gana la promoción de mayor descuento; las promociones NO se acumulan/suman.
- Q: ¿Qué semántica tiene el rollback de un cambio de precio cuando hubo cambios posteriores sobre la misma fecha? → A: El rollback crea un nuevo cambio auditado (origen = rollback) que fija el valor anterior, sin borrar el historial; si existen cambios posteriores sobre la misma (unidad, día), el sistema señala el conflicto y requiere confirmación explícita antes de sobrescribirlos. El caso normal (revertir el último cambio) se aplica directamente.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Representar propiedades, canales, unidades y precios por día (Priority: P1)

El host tiene una o varias propiedades en Medellín, cada una listada en Booking.com (y, en el futuro, otros canales como Airbnb). Necesita que el sistema represente esas propiedades, sus tipos de unidad/habitación, el calendario de disponibilidad por día y el precio por noche de cada unidad y día, en pesos colombianos (COP). La disponibilidad debe compartirse entre canales para no sobrevender.

**Why this priority**: Es la base sobre la que se apoya todo lo demás (consultar precios, asignarlos, sugerirlos). Sin esto no hay producto.

**Independent Test**: Cargar una propiedad con un tipo de unidad y precios/disponibilidad para un rango de fechas, y poder consultar el precio y la disponibilidad de cualquier día. Verificable de forma aislada.

**Acceptance Scenarios**:

1. **Given** una propiedad con un tipo de unidad en Booking.com, **When** se consulta una fecha concreta, **Then** el sistema devuelve el precio por noche (COP) y la disponibilidad de ese día.
2. **Given** una propiedad listada en dos canales, **When** se marca una noche como reservada en un canal, **Then** esa noche figura como no disponible para todos los canales.
3. **Given** una propiedad con varios tipos de unidad, **When** se consulta el calendario, **Then** cada tipo de unidad tiene su propio precio y disponibilidad por día.

---

### User Story 2 - Auditar y revertir cualquier cambio de precio (Priority: P1)

Cada vez que cambia un precio (sea por el host manualmente, por el chat o por aplicar una sugerencia), el sistema registra qué cambió, cuándo, el valor anterior y el nuevo, y el origen del cambio. El host puede deshacer un cambio y volver al valor anterior.

**Why this priority**: Es el principio no negociable de la constitución (III): todo cambio de precio es auditable y reversible. Da confianza para dejar actuar al agente.

**Independent Test**: Cambiar un precio, consultar el registro de auditoría (ver antes/después/origen) y revertirlo, confirmando que vuelve al valor anterior.

**Acceptance Scenarios**:

1. **Given** un precio existente, **When** se cambia su valor, **Then** se crea una entrada de auditoría con valor anterior, nuevo, fecha/hora y origen.
2. **Given** un cambio de precio registrado, **When** el host lo revierte, **Then** el precio vuelve al valor anterior y la reversión también queda registrada.
3. **Given** varios cambios sobre la misma fecha, **When** se consulta el historial, **Then** se ven todos los cambios en orden cronológico con su origen.

---

### User Story 3 - Promociones y reglas de precio (Priority: P2)

El host define promociones (porcentaje o monto, con vigencia y condiciones) y reglas de límites (precio mínimo y máximo por propiedad). El precio efectivo de un día refleja las promociones vigentes, y ningún precio puede quedar fuera de los límites definidos.

**Why this priority**: Necesario para el manejo real de tarifas, pero se apoya en las entidades base (P1).

**Independent Test**: Crear una promoción para un rango de fechas y comprobar que el precio efectivo de esos días baja según la promoción, y que un precio fuera de los límites es rechazado o señalado.

**Acceptance Scenarios**:

1. **Given** un precio base y una promoción vigente del 10%, **When** se consulta el precio efectivo de un día cubierto, **Then** refleja el descuento aplicado.
2. **Given** una regla de precio mínimo, **When** se intenta fijar un precio por debajo del mínimo, **Then** el sistema lo señala como inválido.
3. **Given** dos promociones que se solapan en un día, **When** se calcula el precio efectivo, **Then** se aplica únicamente la de mayor descuento (no se acumulan).

---

### User Story 4 - Reservas, ocupación, eventos y sugerencias (Priority: P2)

El sistema almacena reservas provenientes del canal (fechas, canal de origen, estado) que determinan la ocupación; registra eventos de la ciudad (con fecha, tipo, relevancia, ubicación, deduplicados); y guarda sugerencias de precio del agente (por día/rango, con justificación, score de confianza y estado: propuesta/aprobada/rechazada/aplicada).

**Why this priority**: Es el insumo de la inteligencia de precios (Fases 4–5); se puede construir tras la base.

**Independent Test**: Cargar reservas y eventos, generar una sugerencia asociada a ellos, y mover la sugerencia por sus estados hasta "aplicada".

**Acceptance Scenarios**:

1. **Given** reservas para ciertas noches, **When** se consulta la ocupación de un rango, **Then** refleja las noches reservadas.
2. **Given** un evento en una fecha, **When** se genera una sugerencia, **Then** la sugerencia referencia su justificación (evento/mercado/ocupación) y un score de confianza.
3. **Given** una sugerencia "propuesta", **When** el host la aprueba y se aplica, **Then** su estado pasa a "aplicada" y el cambio de precio resultante queda auditado (US2).
4. **Given** un evento ya registrado, **When** se intenta registrar el mismo evento, **Then** no se crea un duplicado.

---

### User Story 5 - Configuración de LLM e historial de chat (Priority: P3)

El sistema guarda la configuración del LLM (proveedor, modelo para tareas generales, modelo para acciones, parámetros y presupuesto) y el historial de conversaciones del chat, asociando cada acción (p. ej. un cambio de precio) al mensaje que la originó.

**Why this priority**: Soporta la experiencia agéntica y la trazabilidad, pero no bloquea el manejo básico de precios.

**Independent Test**: Guardar una configuración de LLM y una conversación con mensajes, y comprobar que una acción de cambio de precio queda enlazada al mensaje que la provocó.

**Acceptance Scenarios**:

1. **Given** una configuración de LLM guardada, **When** se consulta, **Then** devuelve proveedor, modelos y presupuesto.
2. **Given** una conversación con un cambio de precio originado en un mensaje, **When** se revisa el historial, **Then** el cambio aparece enlazado a ese mensaje (y a su entrada de auditoría).

---

### Edge Cases

- **Fechas sin precio definido**: una fecha sin tarifa explícita debe tener un comportamiento definido (sin precio = no vendible, o hereda de un valor base).
- **Reserva que cruza el cambio de precio**: una reserva multinoche se valora según el precio vigente de cada noche.
- **Promociones solapadas**: si varias promociones aplican al mismo día, gana la de mayor descuento; no se acumulan.
- **Promoción que deja el precio bajo el mínimo**: debe señalarse o acotarse al límite, no aplicarse silenciosamente.
- **Rollback de un cambio ya superado por otro**: si hubo cambios posteriores sobre la misma (unidad, día), el rollback NO sobrescribe en silencio; señala el conflicto y requiere confirmación explícita. El caso normal (revertir el último cambio) se aplica directamente como un nuevo cambio auditado.
- **Evento duplicado con datos ligeramente distintos**: la deduplicación debe basarse en criterios estables (nombre + fecha + lugar).
- **Moneda**: todos los montos de una propiedad son en su moneda (COP); no se mezclan monedas en cálculos.
- **Borrado de una propiedad/unidad con historial**: el historial de auditoría debe preservarse aunque se desactive la entidad.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST representar una o varias propiedades del host, cada una con nombre, ubicación (ciudad) y moneda (COP).
- **FR-002**: El sistema MUST asociar a cada propiedad uno o más canales de venta, indicando cuáles están activos; solo Booking.com está activo inicialmente, pero el modelo MUST admitir otros canales (p. ej. Airbnb) sin rediseño.
- **FR-003**: El sistema MUST representar uno o más tipos de unidad/habitación por propiedad, cada uno con una cantidad de unidades disponibles.
- **FR-004**: El sistema MUST mantener, por tipo de unidad y día, la disponibilidad/ocupación, compartida entre todos los canales de la propiedad.
- **FR-005**: El sistema MUST mantener, por tipo de unidad y día, un precio base por noche en la moneda de la propiedad.
- **FR-006**: El sistema MUST permitir (a nivel de modelo, sin activarlo aún) un ajuste de precio por canal (offset), preservando el espacio para activarlo en el futuro.
- **FR-007**: El sistema MUST calcular un precio efectivo por día a partir del precio base y las promociones vigentes.
- **FR-008**: El sistema MUST soportar promociones/descuentos con tipo (porcentaje o monto), vigencia (rango de fechas) y condiciones, y reflejarlas en el precio efectivo. Cuando varias promociones aplican al mismo día, el sistema MUST usar únicamente la de mayor descuento efectivo; las promociones NO se acumulan.
- **FR-009**: El sistema MUST soportar reglas de precio con límite mínimo y máximo por propiedad, y señalar cuando un precio queda fuera de los límites.
- **FR-010**: El sistema MUST registrar cada cambio de precio con: valor anterior, valor nuevo, fecha/hora, día(s) afectado(s), unidad/propiedad y origen (chat, manual o sugerencia).
- **FR-011**: Los usuarios MUST be able to revertir un cambio de precio registrado, devolviendo el precio a su valor anterior. La reversión se aplica creando un nuevo cambio auditado (origen = rollback), sin borrar el historial. Si existen cambios posteriores sobre la misma (unidad, día), el sistema MUST señalar el conflicto y requerir confirmación explícita antes de sobrescribirlos; el caso normal (revertir el último cambio) se aplica directamente.
- **FR-012**: El sistema MUST almacenar reservas provenientes del canal (fechas, canal de origen, estado) y derivar de ellas la ocupación.
- **FR-013**: El sistema MUST almacenar eventos de la ciudad con fecha, tipo, relevancia/impacto estimado y ubicación, evitando duplicados.
- **FR-014**: El sistema MUST almacenar sugerencias de precio por día o rango, con justificación (referencias a eventos/mercado/ocupación), score de confianza y estado (propuesta, aprobada, rechazada, aplicada).
- **FR-015**: El sistema MUST enlazar una sugerencia aplicada con el cambio de precio (y su auditoría) que produjo.
- **FR-016**: El sistema MUST almacenar la configuración del LLM: proveedor, modelo para tareas generales, modelo para acciones, parámetros y presupuesto.
- **FR-017**: El sistema MUST almacenar conversaciones y mensajes del chat, y enlazar las acciones (p. ej. cambios de precio) con el mensaje que las originó.
- **FR-018**: El sistema MUST preservar el historial de auditoría aunque una propiedad o unidad se desactive.
- **FR-019**: El modelo MUST excluir explícitamente multi-tenancy y autenticación de múltiples usuarios (single-tenant).

### Key Entities *(include if feature involves data)*

- **Propiedad (Property)**: Un alojamiento del host. Atributos: nombre, ciudad, moneda (COP), estado (activa/inactiva). Relaciona: tiene canales, tipos de unidad, reglas de precio, promociones, reservas, sugerencias.
- **Canal (Channel)**: Plataforma de venta de una propiedad (Booking.com, Airbnb, web). Atributos: tipo, estado (activo/inactivo), identificador externo, offset de precio (no activado). La disponibilidad NO es por canal; se comparte a nivel de unidad.
- **Tipo de Unidad (UnitType)**: Tipo de habitación/unidad de una propiedad. Atributos: nombre, cantidad de unidades.
- **Día de Calendario (CalendarDay)**: Estado por unidad y fecha. Atributos: disponibilidad/ocupación (compartida entre canales).
- **Tarifa (Rate / DayPrice)**: Precio por unidad y fecha. Atributos: precio base por noche; precio efectivo derivado; referencia opcional a offset de canal.
- **Regla de Precio (PricingRule)**: Límites por propiedad. Atributos: precio mínimo, precio máximo, consideraciones de paridad (placeholder).
- **Promoción (Promotion)**: Descuento aplicable. Atributos: tipo (porcentaje/monto), valor, vigencia (rango), condiciones, estado.
- **Reserva (Booking)**: Reserva proveniente de un canal. Atributos: fechas (entrada/salida), canal de origen, estado, unidad. Determina la ocupación.
- **Evento (Event)**: Acontecimiento de la ciudad. Atributos: nombre, fecha(s), tipo, relevancia/impacto, ubicación; clave de deduplicación (nombre + fecha + lugar).
- **Sugerencia (PriceSuggestion)**: Recomendación del agente. Atributos: día o rango, precio sugerido, justificación (referencias a eventos/mercado/ocupación), score de confianza, estado (propuesta/aprobada/rechazada/aplicada); enlace al cambio aplicado.
- **Registro de Auditoría (PriceChangeLog)**: Historia de cambios de precio. Atributos: día(s)/unidad/propiedad afectados, valor anterior, valor nuevo, fecha/hora, origen (chat/manual/sugerencia), enlace a la reversión si existe.
- **Configuración de LLM (LLMConfig)**: Atributos: proveedor, modelo general, modelo de acciones, parámetros, presupuesto.
- **Conversación (Conversation) y Mensaje (Message)**: Historial del chat. Atributos: mensajes con rol y contenido; los mensajes pueden enlazar a las acciones/auditorías que originaron.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A partir del modelo, se puede consultar el precio y la disponibilidad de cualquier (propiedad, unidad, día) sin ambigüedad y con un único resultado.
- **SC-002**: El 100% de los cambios de precio quedan registrados con valor anterior, nuevo, origen y marca de tiempo, y cualquiera puede revertirse a su valor anterior.
- **SC-003**: Una noche reservada en un canal aparece como no disponible en todos los canales de la propiedad en el 100% de los casos (cero overbooking en el modelo).
- **SC-004**: El precio efectivo de un día puede explicarse en términos de su precio base y las promociones/reglas aplicadas (trazabilidad del cálculo).
- **SC-005**: Una sugerencia aplicada queda enlazada a su cambio de precio y a su entrada de auditoría en el 100% de los casos.
- **SC-006**: Registrar el mismo evento dos veces no produce duplicados (deduplicación efectiva por nombre + fecha + lugar).
- **SC-007**: El modelo soporta añadir un nuevo canal (p. ej. Airbnb) sin modificar las entidades existentes de propiedad/unidad/tarifa (solo activación).

## Assumptions

- **Single-tenant**: un solo host/operador; sin gestión de múltiples cuentas ni roles.
- **Moneda única por propiedad**: COP; no hay conversión de divisas en esta etapa.
- **Booking.com es el único canal activo**; Airbnb y otros quedan modelados pero inactivos.
- **Precio a nivel de tipo de unidad y día** (no por reserva ni por huésped individual).
- **Disponibilidad compartida entre canales** vía el channel manager (Beds24); el modelo no duplica disponibilidad por canal.
- **Offsets de precio por canal, promociones específicas de Airbnb y paridad avanzada** se modelan como espacio reservado pero NO se implementan en esta feature.
- **La fuente de verdad operativa de disponibilidad/reservas/precios externos es el channel manager**; este modelo es la representación local que se sincroniza con él (la sincronización se especifica en otra feature).
- **Identidad/seguridad**: un mecanismo simple de acceso del host (fuera del alcance de esta feature de datos).
