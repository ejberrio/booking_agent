# Feature Specification: Observabilidad en producción

**Feature Branch**: `010-observability`
**Created**: 2026-06-28
**Status**: Draft
**Input**: User description: "Seguimiento de errores (Sentry) en API y web, logging estructurado de la API, y un endpoint de estado enriquecido — para que el operador se entere cuando algo falla y entienda el estado del sistema sin revisar logs a mano."

## Clarifications

### Session 2026-06-28

- Q: El endpoint de estado reporta 'Beds24 conectado/no'. ¿Cómo lo verifica? → A: Chequeo en vivo pero **cacheado ~5 min** (estado real sin consumir cuota ni añadir latencia en cada consulta).
- Q: ¿Formato del logging estructurado de la API? → A: **Líneas legibles tipo key=value** (p. ej. `method=GET path=/pricing/calendar status=200 ms=45`), fáciles de leer en el visor de logs del proveedor.
- Q: ¿Muestreo de trazas de rendimiento (v1)? → A: **0% — solo errores** (sin trazas de performance; mínima cuota).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El operador se entera de los errores (Priority: P1)

Cuando ocurre una excepción no controlada en la API o en la web, el sistema la captura y la reporta a un servicio de seguimiento de errores con contexto suficiente (entorno, versión, identificador de la operación) para depurarla, y puede alertar al operador. Así el operador no depende de que un huésped o él mismo "tropiece" con el fallo.

**Why this priority**: Es el mayor valor de la observabilidad: enterarse de los fallos reales en producción (varios bugs de esta app se hallaron a mano). Sin esto, los errores pasan desapercibidos.

**Independent Test**: Forzar un error controlado de prueba en la API y en la web y verificar que aparece en el servicio de seguimiento con su contexto; y que, sin configurar el servicio, la app sigue funcionando igual (no-op).

**Acceptance Scenarios**:

1. **Given** el seguimiento de errores configurado, **When** ocurre una excepción no controlada en la API, **Then** se reporta con entorno, versión y contexto, sin incluir secretos.
2. **Given** el seguimiento de errores configurado, **When** ocurre un error no controlado en la web, **Then** se reporta igual.
3. **Given** que NO hay seguimiento configurado (sin credencial), **When** arranca la app, **Then** funciona con normalidad (no-op) y no falla por ello.
4. **Given** cualquier reporte de error, **When** se inspecciona, **Then** no contiene secretos (credenciales, tokens) ni datos personales innecesarios.

---

### User Story 2 - Logs estructurados y legibles de la API (Priority: P2)

Cada petición a la API deja un registro estructurado (método, ruta, código de respuesta, duración) y los errores incluyen su traza, de forma legible en los logs del proveedor de hosting. El operador puede seguir qué pasó y cuánto tardó, sin ruido ni secretos.

**Why this priority**: Complementa el seguimiento de errores para diagnóstico cotidiano (latencias, rutas que fallan), pero el valor crítico (enterarse de fallos) ya lo da US1.

**Independent Test**: Hacer varias peticiones (algunas que fallen) y verificar que cada una deja una línea estructurada con método/ruta/status/duración, y que los errores muestran la traza, sin secretos.

**Acceptance Scenarios**:

1. **Given** la API en marcha, **When** llega una petición, **Then** se registra una línea con método, ruta, status y duración.
2. **Given** una petición que provoca un error, **When** se procesa, **Then** el registro incluye la traza del error.
3. **Given** cualquier registro, **When** se revisa, **Then** no aparece ningún secreto.

---

### User Story 3 - Endpoint de estado del sistema (Priority: P2)

El operador (o un chequeo externo) consulta un endpoint de estado que resume en un vistazo: versión de la app, base de datos arriba/abajo, conexión con el Channel Manager (Beds24) ok/no, y cuántas incidencias de publicación están abiertas. Así sabe si todo está sano sin abrir varias herramientas.

**Why this priority**: Da una foto rápida del sistema, útil para verificación y soporte; complementa pero no reemplaza el seguimiento de errores.

**Independent Test**: Consultar el endpoint de estado y obtener versión, estado de la base de datos, estado de Beds24 y conteo de incidencias abiertas, coherentes con la realidad.

**Acceptance Scenarios**:

1. **Given** el sistema sano, **When** se consulta el estado, **Then** devuelve versión, base de datos "ok", Beds24 "conectado" y el conteo de incidencias abiertas.
2. **Given** la base de datos caída, **When** se consulta el estado, **Then** lo refleja como degradado.
3. **Given** incidencias de publicación abiertas, **When** se consulta el estado, **Then** el conteo coincide con las incidencias reales.

---

### Edge Cases

- **Sin credencial del servicio de errores**: la app arranca y opera normal (no-op); no se cae ni ralentiza por ello.
- **El servicio de errores no responde**: no debe bloquear ni romper las peticiones del usuario (el reporte es best-effort).
- **Secretos/PII**: ningún reporte ni log debe contener credenciales, tokens ni datos personales innecesarios (se filtran).
- **Endpoint de estado y dependencias caídas**: si una comprobación (DB o Beds24) falla o tarda, el endpoint responde igual marcando esa parte como degradada, sin colgarse.
- **Ruido de logs**: el registro por petición no debe inundar ni duplicar; nivel configurable.
- **Coste/cuota del servicio de errores**: para v1, el muestreo de rendimiento/trazas es mínimo (solo errores), para no exceder cuotas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST capturar las excepciones no controladas de la API y de la web y reportarlas a un servicio de seguimiento de errores, con entorno (producción), versión/release y un identificador de la operación.
- **FR-002**: El seguimiento de errores MUST funcionar como NO-OP si no hay credencial configurada: la app arranca y opera con normalidad sin él.
- **FR-003**: Ningún reporte de error ni registro de log MUST contener secretos (credenciales, tokens, cadenas de conexión) ni datos personales innecesarios.
- **FR-004**: La API MUST registrar, por cada petición, un log estructurado en **líneas legibles tipo key=value** (método, ruta, código de respuesta y duración); los errores MUST incluir la traza.
- **FR-005**: El nivel/verbosidad del logging MUST ser configurable por entorno.
- **FR-006**: El sistema MUST exponer un endpoint de estado que reporte: versión de la app, estado de la base de datos, estado de la conexión con el Channel Manager (Beds24) y el conteo de incidencias de publicación abiertas. La comprobación de Beds24 es **en vivo pero cacheada (~5 min)** para no consumir cuota ni añadir latencia en cada consulta.
- **FR-007**: El endpoint de estado MUST responder aunque una dependencia (base de datos o Channel Manager) esté caída o lenta, marcándola como degradada, sin colgarse.
- **FR-008**: El reporte de errores y la consulta de estado MUST ser best-effort: si el servicio externo o una dependencia fallan, no deben romper la petición del usuario.
- **FR-009**: La configuración del servicio de errores (credencial) MUST hacerse por variable de entorno; la app NO crea ni gestiona esa cuenta (acción del operador).
- **FR-010**: El endpoint de estado MUST quedar protegido como el resto de la app (tras el acceso de la web/proxy), salvo el chequeo de salud básico que el proveedor de hosting ya usa.

### Key Entities

- **Reporte de error**: una excepción capturada con su contexto (entorno, versión, identificador de operación, traza), enviada al servicio externo; sin secretos.
- **Registro de petición (log estructurado)**: línea por petición con método, ruta, status y duración; errores con traza.
- **Estado del sistema**: resumen consultable — versión, base de datos (ok/degradado), Channel Manager (conectado/no), nº de incidencias de publicación abiertas.
- **Incidencia de publicación** *(existente, `SyncIssue`)*: fallo al publicar al Channel Manager; su conteo abierto alimenta el estado.
- **Configuración de observabilidad**: credencial del servicio de errores y nivel de logging, por variables de entorno.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una excepción no controlada en la API o en la web aparece en el servicio de seguimiento de errores en menos de 1 minuto, con contexto suficiente para ubicar el archivo/operación.
- **SC-002**: Sin credencial configurada, la app arranca y opera con normalidad (0 fallos atribuibles a la observabilidad).
- **SC-003**: El 100% de los reportes y logs revisados no contienen secretos ni datos personales innecesarios.
- **SC-004**: Cada petición a la API deja exactamente un registro estructurado con método, ruta, status y duración.
- **SC-005**: El endpoint de estado refleja correctamente la realidad (versión, base de datos, Beds24, conteo de incidencias) y responde en menos de 2 segundos incluso con una dependencia degradada.
- **SC-006**: Ninguna falla del servicio externo de errores o de una dependencia rompe una petición del usuario.

## Assumptions

- **Servicio de errores**: se usa un servicio externo estándar de seguimiento de errores; su credencial la crea y configura el operador (por variable de entorno). v1 prioriza errores; el muestreo de trazas de rendimiento es **0%** (solo errores, mínima cuota) — decidido en clarify.
- **Estado de Beds24 cacheado** (decidido en clarify): la comprobación en vivo se cachea ~5 min.
- **Formato de logs** (decidido en clarify): líneas legibles key=value en los logs del proveedor.
- **No-op sin credencial**: la integración es opcional en arranque; sin credencial, la app no la usa y no se ve afectada.
- **Logs del proveedor**: el logging estructurado se consume en los logs del proveedor de hosting (ya disponibles); no se monta un agregador de logs propio en v1.
- **Estado tras acceso**: el endpoint de estado se protege como el resto de la app; el chequeo de salud básico del proveedor permanece.
- **Reutiliza lo existente**: aprovecha el `/health` (liveness + DB) y el registro de incidencias `SyncIssue` ya presentes.
- **Single-tenant**: un host; sin necesidad de multi-proyecto ni segmentación de errores por cliente.
- **Fuera de alcance v1**: dashboards de métricas (Prometheus/Grafana), tracing distribuido completo, APM avanzado, paneles de negocio y alertas complejas más allá de las del servicio por defecto.
