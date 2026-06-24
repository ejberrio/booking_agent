# Feature Specification: Conector de Channel Manager (Beds24)

**Feature Branch**: `002-beds24-connector`  
**Created**: 2026-06-24  
**Status**: Draft  
**Input**: Integración provider-agnostic que sincroniza el modelo de datos local (feature 001) con Beds24, el cual a su vez sincroniza con Booking.com: conectar, leer (propiedades, unidades, calendario, precios, reservas) y escribir (precios por día/rango) con auditoría, reconciliación y manejo de errores. Solo Booking activo; single-tenant.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conectar con el Channel Manager y validar la conexión (Priority: P1)

El host configura sus credenciales de Beds24 (almacenadas de forma segura, fuera del repositorio) y el sistema valida que la conexión funciona, identificando las propiedades disponibles en la cuenta.

**Why this priority**: Sin una conexión válida no es posible leer ni escribir nada. Es la puerta de entrada.

**Independent Test**: Configurar credenciales y ejecutar una "prueba de conexión" que confirme acceso y liste las propiedades de la cuenta; con credenciales inválidas, devuelve un error claro sin exponer secretos.

**Acceptance Scenarios**:

1. **Given** credenciales válidas, **When** se ejecuta la prueba de conexión, **Then** el sistema confirma acceso y devuelve las propiedades de la cuenta.
2. **Given** credenciales inválidas o ausentes, **When** se ejecuta la prueba de conexión, **Then** el sistema reporta un error claro y no realiza más operaciones.
3. **Given** una conexión establecida, **When** se consultan los datos de conexión, **Then** los secretos nunca se muestran ni se registran en logs.

---

### User Story 2 - Importar datos desde el Channel Manager (lectura) (Priority: P1)

El sistema trae desde Beds24 las propiedades, tipos de unidad, calendario/disponibilidad, precios actuales y reservas, y los refleja en el modelo local (feature 001), mapeando los identificadores externos.

**Why this priority**: El host necesita ver en la plataforma el estado real (precios, disponibilidad, ocupación) antes de poder gestionarlo.

**Independent Test**: Ejecutar una importación y verificar que las propiedades, unidades, días de calendario, precios y reservas aparecen en el modelo local con su `external_ref` mapeado.

**Acceptance Scenarios**:

1. **Given** una conexión válida, **When** se ejecuta la importación, **Then** las propiedades y tipos de unidad quedan creados/actualizados localmente con su identificador externo.
2. **Given** datos de calendario y precios en el Channel Manager, **When** se importan, **Then** la disponibilidad y los precios por día se reflejan localmente.
3. **Given** reservas existentes, **When** se importan, **Then** la ocupación local refleja esas reservas.
4. **Given** una segunda importación, **When** hay cambios remotos, **Then** solo se actualiza lo que cambió (sincronización incremental) sin duplicar entidades.

---

### User Story 3 - Publicar precios (escritura) con verificación y auditoría (Priority: P1)

El host (o el agente, tras confirmación) fija un precio por día o por rango y el sistema lo envía a Beds24; verifica que la escritura se aplicó y registra el cambio en la auditoría local.

**Why this priority**: Es el valor central de la plataforma: cambiar precios que lleguen a Booking. Sin esto, la herramienta solo lee.

**Independent Test**: Fijar un precio para un día y un rango, confirmar que el Channel Manager refleja el nuevo valor y que existe la entrada de auditoría correspondiente.

**Acceptance Scenarios**:

1. **Given** una conexión válida y un precio nuevo para un día, **When** se publica, **Then** el Channel Manager refleja ese precio y se crea una entrada de auditoría con origen correspondiente.
2. **Given** un rango de fechas, **When** se publica un precio para el rango, **Then** todos los días del rango quedan actualizados y verificados.
3. **Given** una publicación que falla parcialmente, **When** se reintenta, **Then** la operación es idempotente (no duplica ni corrompe) y al final el estado es consistente o el fallo queda claramente reportado.
4. **Given** límites de tasa del proveedor, **When** se publican muchos cambios, **Then** el sistema respeta el rate limit con espera/reintentos sin perder cambios.

---

### User Story 4 - Reconciliación y manejo de errores (Priority: P2)

El sistema detecta discrepancias entre el estado local y el remoto (p. ej. un precio cambiado directamente en Beds24/Booking) y las reporta para que el host decida, sin sobrescribir en silencio. Los errores de sincronización quedan registrados para alertar.

**Why this priority**: Da confianza y robustez, pero se apoya en la lectura/escritura ya existentes.

**Independent Test**: Provocar una discrepancia (precio distinto local vs remoto) y verificar que el sistema la detecta, la reporta y no sobrescribe sin decisión del host; provocar un error de sincronización y verificar que queda registrado.

**Acceptance Scenarios**:

1. **Given** un precio distinto entre local y remoto, **When** se reconcilia, **Then** se reporta la discrepancia y no se sobrescribe sin decisión del host.
2. **Given** un error de comunicación con el proveedor, **When** ocurre durante una sincronización, **Then** se registra el error con contexto suficiente para alertar y diagnosticar.
3. **Given** una reserva nueva en el remoto, **When** se reconcilia, **Then** la disponibilidad local se actualiza (la fuente de verdad de reservas/disponibilidad es el remoto).

---

### User Story 5 - Sincronización incremental programada y re-sync manual (Priority: P3)

El sistema sincroniza periódicamente de forma automática y permite forzar una sincronización manual cuando el host lo necesite.

**Why this priority**: Conveniencia y frescura de datos; no bloquea las operaciones manuales.

**Independent Test**: Programar/disparar una sincronización y verificar que actualiza datos cambiados desde la última corrida, registrando su resultado.

**Acceptance Scenarios**:

1. **Given** una sincronización previa, **When** corre la siguiente (programada o manual), **Then** procesa solo lo cambiado desde la última corrida y registra su resultado (éxito/errores, conteos).

---

### Edge Cases

- **Credenciales expiradas/revocadas**: el sistema lo detecta, marca la conexión como inválida y guía a renovar credenciales, sin perder datos locales.
- **Propiedad o unidad eliminada en el remoto**: se marca como inactiva localmente, preservando el historial de auditoría.
- **Escritura aceptada por el proveedor pero no reflejada al verificar**: se reporta como inconsistencia para reintento/decisión.
- **Doble ejecución de una sincronización**: debe ser idempotente (no duplica entidades ni reservas).
- **Diferencia de zona horaria/fechas** entre local y proveedor: las fechas de calendario se alinean a la fecha de la propiedad.
- **Cambio de moneda en el proveedor**: se respeta la moneda de la propiedad; montos inconsistentes se señalan.
- **Rate limit alcanzado a mitad de un lote**: el lote se reanuda respetando el límite sin perder cambios.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST exponer una interfaz común de Channel Manager (lectura de propiedades, unidades, calendario/disponibilidad, precios y reservas; escritura de precios por día y por rango) independiente del proveedor concreto.
- **FR-002**: El sistema MUST implementar dicha interfaz para Beds24 como primer (y por ahora único) proveedor, sin filtrar detalles propietarios de Beds24 al dominio.
- **FR-003**: El sistema MUST autenticar/conectar con el proveedor usando credenciales almacenadas de forma segura y cifrada, NUNCA en el repositorio ni en logs.
- **FR-004**: El sistema MUST ofrecer una prueba de conexión que confirme acceso y liste las propiedades de la cuenta, con errores claros ante credenciales inválidas.
- **FR-005**: El sistema MUST importar propiedades, tipos de unidad, calendario/disponibilidad, precios actuales y reservas hacia el modelo local, mapeando identificadores externos (`external_ref`).
- **FR-006**: El sistema MUST realizar la importación de forma incremental (solo cambios desde la última sincronización) sin duplicar entidades.
- **FR-007**: El sistema MUST publicar precios por día y por rango al proveedor y verificar que la escritura se aplicó.
- **FR-008**: El sistema MUST registrar en la auditoría local (feature 001) todo cambio de precio que origine, con el origen correspondiente; los cambios deben ser reversibles.
- **FR-009**: El sistema MUST manejar fallos parciales de escritura con reintentos idempotentes y dejar el estado final consistente o el fallo claramente reportado.
- **FR-010**: El sistema MUST respetar los límites de tasa del proveedor (espera/backoff y reanudación) sin perder cambios.
- **FR-011**: El sistema MUST detectar discrepancias entre el estado local y el remoto y reportarlas SIN sobrescribir en silencio (el host decide).
- **FR-012**: El sistema MUST tratar las reservas y la disponibilidad del proveedor como fuente de verdad y reflejarlas en la ocupación local.
- **FR-013**: El sistema MUST registrar cada corrida de sincronización (dirección, marca de tiempo, resultado, conteos y errores) para diagnóstico y alerta.
- **FR-014**: El sistema MUST permitir sincronización manual (bajo demanda) además de la programada.
- **FR-015**: El sistema MUST limitar el alcance al canal Booking.com activo; otros canales (Airbnb) quedan inactivos (channel-aware).
- **FR-016**: El sistema MUST detectar credenciales expiradas/revocadas y marcar la conexión como inválida sin perder datos locales.

### Key Entities *(include if feature involves data)*

- **Conexión de Channel Manager (ChannelManagerConnection)**: Cuenta conectada. Atributos: proveedor (beds24), referencia a credenciales (no el secreto), estado (conectado/inválido), última verificación.
- **Corrida de Sincronización (SyncRun)**: Una ejecución. Atributos: dirección (entrante/saliente), inicio/fin, resultado (éxito/parcial/error), conteos (creados/actualizados), marca de la última posición incremental.
- **Error/Discrepancia de Sincronización (SyncIssue)**: Atributos: tipo (error de comunicación, discrepancia de precio, escritura no verificada), entidad afectada, detalle, estado (abierto/resuelto).
- **Mapeo externo**: Se apoya en los `external_ref` ya presentes en las entidades de la feature 001 (propiedad, unidad, reserva); esta feature los puebla y mantiene.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con credenciales válidas, la prueba de conexión confirma acceso y lista las propiedades; con credenciales inválidas, devuelve un error claro y no realiza cambios.
- **SC-002**: Tras una importación, el 100% de las propiedades, unidades, días de calendario, precios y reservas del alojamiento quedan reflejados localmente con su identificador externo.
- **SC-003**: Un precio publicado para un día o rango se refleja en el proveedor y queda verificado; cada cambio publicado tiene su entrada de auditoría (trazabilidad 100%).
- **SC-004**: Ninguna discrepancia entre local y remoto se sobrescribe sin decisión del host (cero sobrescrituras silenciosas).
- **SC-005**: Ningún secreto de credenciales aparece en el repositorio ni en los registros (logs).
- **SC-006**: Una segunda sincronización sin cambios remotos no crea entidades duplicadas (idempotencia).
- **SC-007**: Ante límites de tasa del proveedor, no se pierden cambios: todos los precios solicitados terminan aplicados o reportados.

## Assumptions

- **Método de autenticación de Beds24 (V1 con apiKey + propKey por propiedad, o V2 con invite code → refresh token) es un detalle de implementación** que se decide en el plan/spike; la interfaz del conector es independiente de esa elección. El host ya generó una credencial V1.
- **Credenciales** se gestionan en configuración local cifrada (.env/secret manager), nunca en el repositorio.
- **Single-tenant**: una sola cuenta de Channel Manager del host.
- **Solo Booking.com activo**; la disponibilidad es compartida por unidad (no por canal).
- **El modelo de datos local (feature 001) ya existe** y es el destino/fuente local de la sincronización.
- **Fuente de verdad**: reservas y disponibilidad provienen del proveedor; los precios los fija el host vía la plataforma y se publican al proveedor.
- **El motor de precios/promociones, la UI y el agente conversacional están fuera de alcance** de esta feature.
- **Frecuencia de sincronización programada**: por defecto periódica (configurable); además sincronización manual bajo demanda.
