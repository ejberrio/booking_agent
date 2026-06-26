# Feature Specification: Inteligencia de mercado y sugerencias de precio

**Feature Branch**: `005-market-intelligence`  
**Created**: 2026-06-26  
**Status**: Draft  
**Input**: Descubrir eventos en Medellín (búsqueda web), monitorear precios de mercado por ubicación y generar sugerencias de precio por día (eventos + ocupación + mercado) con justificación y confianza; el host revisa y aplica reutilizando el motor de precios (003). Single-tenant, COP, solo Booking.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Descubrir e ingestar eventos de Medellín (Priority: P1)

El sistema busca en la web eventos relevantes en Medellín (conciertos, ferias, convenciones, festivos, festivales) con su fecha, tipo, relevancia y ubicación, y los guarda sin duplicar.

**Why this priority**: Los eventos son el principal disparador de cambios de precio; sin ellos no hay inteligencia útil.

**Independent Test**: Ejecutar un escaneo de eventos y verificar que aparecen eventos con fecha/tipo/relevancia; repetir el escaneo y comprobar que no se duplican.

**Acceptance Scenarios**:

1. **Given** una búsqueda de eventos para un período, **When** se ejecuta, **Then** se registran eventos con fecha, tipo, relevancia y ubicación.
2. **Given** un evento ya registrado, **When** se vuelve a descubrir, **Then** no se crea un duplicado.
3. **Given** un resultado de búsqueda sin fecha clara, **When** se procesa, **Then** se descarta o se marca para revisión, sin corromper el calendario.

---

### User Story 2 - Generar sugerencias de precio explicables (Priority: P1)

El sistema genera sugerencias de precio por día/rango combinando eventos (relevancia), ocupación local y una referencia de mercado, cada una con una justificación legible ("Feria de las Flores, alta ocupación") y un score de confianza.

**Why this priority**: Es el valor central de la fase: proponer cambios fundamentados que el host pueda aprobar.

**Independent Test**: Con un evento de alta relevancia y ocupación alta en unas fechas, generar sugerencias y verificar que proponen subir el precio esos días, con justificación y confianza.

**Acceptance Scenarios**:

1. **Given** un evento de alta relevancia en ciertas fechas, **When** se generan sugerencias, **Then** proponen un ajuste al alza esos días con una justificación que menciona el evento.
2. **Given** una sugerencia generada, **When** se inspecciona, **Then** incluye justificación legible, score de confianza y el día/rango afectado.
3. **Given** un período sin eventos ni señales, **When** se generan sugerencias, **Then** no se proponen cambios injustificados.

---

### User Story 3 - Revisar, aprobar/rechazar y aplicar sugerencias (Priority: P1)

El host lista las sugerencias vigentes, las aprueba o rechaza; al aprobar+aplicar, se usa el motor de precios (003): valida límites, audita (origen=sugerencia) y publica el efectivo a Beds24. Nada se aplica sin aprobación.

**Why this priority**: Cierra el ciclo (de la sugerencia al precio publicado) con human-in-the-loop.

**Independent Test**: Aprobar una sugerencia y verificar que el precio cambió, quedó auditado (origen=sugerencia) y se publicó; rechazar otra y verificar que no cambió nada.

**Acceptance Scenarios**:

1. **Given** una sugerencia propuesta, **When** el host la aprueba y aplica, **Then** el precio se fija, se audita (origen=sugerencia) y se publica al canal; la sugerencia queda "aplicada".
2. **Given** una sugerencia propuesta, **When** el host la rechaza, **Then** no cambia ningún precio y la sugerencia queda "rechazada".
3. **Given** una sugerencia cuyo precio violaría los límites, **When** se intenta aplicar, **Then** se señala y no se aplica.

---

### User Story 4 - Monitoreo de precios de mercado por ubicación (Priority: P2)

El sistema obtiene una referencia de precio de mercado (promedio/competencia de la zona) por ubicación y fecha, que alimenta las sugerencias.

**Why this priority**: Mejora la calidad de las sugerencias, pero estas pueden generarse con eventos+ocupación si el mercado no está disponible.

**Independent Test**: Obtener una referencia de mercado para una zona/fecha y verificar que las sugerencias la consideran (p. ej. proponen acercarse a la referencia).

**Acceptance Scenarios**:

1. **Given** una referencia de mercado para una fecha, **When** se generan sugerencias, **Then** la justificación/cálculo la tienen en cuenta.
2. **Given** que la referencia de mercado no está disponible, **When** se generan sugerencias, **Then** se generan igualmente con eventos+ocupación, sin fallar.

---

### User Story 5 - Escaneo programado diario (Priority: P2)

Un job diario escanea eventos y mercado y genera/actualiza sugerencias automáticamente, registrando cada corrida (resultado, conteos).

**Why this priority**: Mantiene las sugerencias frescas sin intervención; no bloquea el uso manual.

**Independent Test**: Ejecutar el escaneo y verificar que genera/actualiza sugerencias y registra la corrida.

**Acceptance Scenarios**:

1. **Given** una corrida diaria, **When** se ejecuta, **Then** se actualizan eventos y mercado y se generan/actualizan sugerencias, registrando la corrida.
2. **Given** una segunda corrida, **When** no hay novedades, **Then** no se duplican eventos ni sugerencias equivalentes.

---

### User Story 6 - Consultar sugerencias por el agente (Priority: P3)

El agente conversacional puede consultar las sugerencias vigentes como una herramienta de lectura (p. ej. "¿qué me sugieres para agosto?").

**Why this priority**: Conecta la inteligencia con la conversación; conveniencia, no bloqueante.

**Independent Test**: Preguntar al agente por sugerencias de un período y verificar que responde con las sugerencias reales (sin inventar).

**Acceptance Scenarios**:

1. **Given** sugerencias vigentes para un período, **When** el host pregunta al agente, **Then** responde con esas sugerencias (justificación y día/rango), basándose en los datos.

---

### Edge Cases

- **Evento sin fecha o ambiguo**: se descarta o se marca para revisión; no entra al calendario como dato sucio.
- **Resultados de búsqueda irrelevantes/duplicados**: se filtran/deduplican (no se proponen sugerencias por ruido).
- **Sin ocupación ni mercado disponibles**: las sugerencias se basan en lo que haya (p. ej. solo eventos) o no se proponen, sin fallar.
- **Sugerencia que excede límites de precio**: se señala y no se aplica.
- **Límite/costo de la API de búsqueda alcanzado**: el escaneo se detiene con gracia y reporta; usa caché para no repetir consultas.
- **Sugerencia ya aplicada o rechazada**: no se vuelve a proponer idéntica en la siguiente corrida.
- **Doble corrida del escaneo**: idempotente (no duplica eventos ni sugerencias equivalentes).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST descubrir eventos de Medellín mediante una búsqueda web detrás de una interfaz provider-agnostic, extrayendo fecha, tipo, relevancia y ubicación.
- **FR-002**: El sistema MUST almacenar los eventos con deduplicación idempotente (no duplica el mismo evento) y descartar/marcar los que no tengan fecha utilizable.
- **FR-003**: El sistema MUST obtener una referencia de precio de mercado por ubicación y fecha detrás de una interfaz provider-agnostic; si no está disponible, las sugerencias se generan igualmente.
- **FR-004**: El sistema MUST generar sugerencias de precio por día/rango combinando eventos (relevancia), ocupación local y referencia de mercado, mediante una heurística **explicable**.
- **FR-005**: Cada sugerencia MUST incluir el día/rango, el precio sugerido, una justificación legible y un score de confianza.
- **FR-006**: El sistema MUST NO proponer cambios cuando no hay señales que los justifiquen.
- **FR-007**: El host MUST poder listar, aprobar y rechazar sugerencias.
- **FR-008**: Aprobar+aplicar una sugerencia MUST usar el motor de precios (003): validar límites, auditar con origen=sugerencia y publicar el efectivo al canal; la sugerencia pasa a "aplicada".
- **FR-009**: El sistema MUST NO aplicar ninguna sugerencia sin aprobación del host (human-in-the-loop) y MUST mantener las aplicaciones auditadas y reversibles.
- **FR-010**: Una sugerencia cuyo precio violaría los límites de la propiedad MUST señalarse y no aplicarse.
- **FR-011**: El sistema MUST ofrecer un escaneo programado (diario) que actualice eventos/mercado y genere/actualice sugerencias, registrando cada corrida (resultado, conteos).
- **FR-012**: El escaneo MUST ser idempotente: una segunda corrida sin novedades no duplica eventos ni sugerencias equivalentes; no re-propone sugerencias ya aplicadas o rechazadas.
- **FR-013**: El sistema MUST acotar el costo de la búsqueda web (bajo volumen, respeto de límites y uso de caché) y degradar con gracia si se alcanza el límite.
- **FR-014**: El agente conversacional MUST poder consultar las sugerencias vigentes como herramienta de lectura, sin inventar datos.
- **FR-015**: El alcance MUST limitarse a Medellín, COP, single-tenant y canal Booking.

### Key Entities *(include if feature involves data)*

Reutiliza `Event` y `PriceSuggestion` (con su justificación, confianza y estados proposed/approved/rejected/applied) y `event_service`/`suggestion_service` de la feature 001; el motor de precios (003) aplica y publica. Conceptos propios:

- **Referencia de mercado (MarketReference)**: precio de referencia por ubicación/zona y fecha, con su origen (cómo se obtuvo); alimenta las sugerencias.
- **Corrida de inteligencia (IntelligenceRun)**: una ejecución del escaneo (inicio/fin, resultado, conteos de eventos/sugerencias, errores) para diagnóstico.
- **Resultado de búsqueda de evento (EventCandidate)**: dato transitorio extraído de la búsqueda antes de normalizarse/deduplicarse en `Event`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tras un escaneo, los eventos relevantes del período quedan registrados con fecha/tipo/relevancia, sin duplicados (repetir el escaneo no crea duplicados).
- **SC-002**: Cada sugerencia generada tiene día/rango, precio sugerido, justificación legible y score de confianza (100%).
- **SC-003**: Un evento de alta relevancia con ocupación alta produce una sugerencia al alza esos días, con justificación que lo menciona.
- **SC-004**: Ninguna sugerencia se aplica sin aprobación del host (0% de aplicaciones automáticas); las aplicadas quedan auditadas con origen=sugerencia y son reversibles.
- **SC-005**: Una sugerencia fuera de los límites de precio nunca se aplica (100%).
- **SC-006**: El escaneo diario es idempotente: una segunda corrida sin novedades no duplica eventos ni sugerencias equivalentes.
- **SC-007**: Si la referencia de mercado no está disponible, las sugerencias se generan igualmente (sin fallo).

## Assumptions

- **Reutiliza** `Event`/`PriceSuggestion` y `event_service`/`suggestion_service` (001), el motor de precios (003) para aplicar/publicar y el conector (002).
- **Heurística explicable** para las sugerencias (reglas transparentes sobre relevancia de evento, ocupación y referencia de mercado), no una caja negra; los parámetros/umbrales son configurables.
- **Búsqueda web** con el proveedor configurado (Tavily), detrás de una interfaz; bajo volumen y con caché para acotar costo.
- **Referencia de mercado**: se modela detrás de una interfaz; su fuente concreta (derivada de búsqueda web, baseline configurable, etc.) se decide en el plan; las sugerencias no dependen de que exista.
- **Single-tenant, COP, Medellín, solo Booking**; la auditoría usa origen=sugerencia.
- **Fuera de alcance**: la UI/dashboard de revisión (Fase 6; aquí backend + endpoints), otros canales (Airbnb) y el despliegue (Fase 7).
- **Pruebas** con búsqueda web y mercado **simulados** (sin llamar a APIs reales ni gastar créditos).
