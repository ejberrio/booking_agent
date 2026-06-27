# Feature Specification: Despliegue en producción (Railway + Neon)

**Feature Branch**: `007-production-deploy`
**Created**: 2026-06-26
**Status**: Draft
**Input**: User description: "Despliegue en producción de Booking_AI_Agent: web (Next.js) y api (FastAPI) en Railway, base de datos Postgres en Neon (tier gratis). Que el host pueda usar la app desde una URL pública, segura y estable, sin gestionar servidores."

## Clarifications

### Session 2026-06-26

- Q: ¿Cómo debe correr en producción el escaneo de eventos (Tavily) que alimenta las sugerencias? → A: Cron diario en Railway (job programado 1×/día, automático).
- Q: ¿Cómo se dispara una nueva versión (deploy) en Railway? → A: Auto al hacer push a `main` (despliegue continuo).
- Q: ¿Qué profundidad debe tener el chequeo de salud (/health) en producción? → A: Liveness + verificación de conexión a la base de datos.
- Q: Ante una eventual pérdida de datos de la base, ¿qué postura de respaldo adoptamos para v1? → A: Re-importar desde Beds24 (fuente de verdad); sin respaldos extra en v1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El host accede a la app en una URL pública y segura (Priority: P1)

El host (único usuario) abre la dirección pública de la aplicación desde cualquier dispositivo, ingresa su contraseña y empieza a gestionar precios. No necesita su computadora ni levantar nada localmente.

**Why this priority**: Es el objetivo central del despliegue: pasar de "corre en mi máquina" a "está disponible siempre, en línea". Sin esto, nada del producto es usable en el día a día.

**Independent Test**: Visitar la URL pública de la web en un navegador limpio, iniciar sesión con la contraseña, y confirmar que cargan el panel, el calendario y el chat con datos reales servidos por la API en línea.

**Acceptance Scenarios**:

1. **Given** la app desplegada, **When** el host abre la URL pública sin sesión, **Then** se le pide la contraseña antes de mostrar cualquier dato.
2. **Given** la contraseña correcta, **When** inicia sesión, **Then** ve el panel y el calendario con precios reales obtenidos de la API en producción.
3. **Given** la app en línea, **When** el host la abre desde otro dispositivo/red, **Then** funciona igual sin configuración local.

---

### User Story 2 - Operador despliega y actualiza siguiendo una guía reproducible (Priority: P1)

El operador (el propio host con rol técnico) sigue una guía paso a paso para crear los servicios en línea, configurar las variables de entorno y publicar la primera versión; y luego puede volver a desplegar una nueva versión repitiendo un proceso conocido.

**Why this priority**: Un despliegue que no se puede repetir ni actualizar no es sostenible. La reproducibilidad es lo que permite corregir y evolucionar sin romper producción.

**Independent Test**: Con el repositorio y la guía, una persona puede llevar la app desde cero hasta una URL pública funcional, y luego publicar un cambio menor y verlo reflejado en línea.

**Acceptance Scenarios**:

1. **Given** la guía y el repositorio, **When** el operador sigue los pasos, **Then** obtiene la web y la API en línea conectadas a la base de datos gestionada.
2. **Given** un cambio en el código fuente, **When** se publica una nueva versión, **Then** la actualización del esquema de datos se aplica automáticamente y la app sigue funcionando.
3. **Given** una variable de configuración faltante o inválida, **When** arranca el servicio, **Then** el fallo es claro y atribuible a esa variable (no un error genérico).

---

### User Story 3 - Verificación de salud post-despliegue (Priority: P2)

Tras desplegar, el operador comprueba en minutos que todo quedó sano: la API responde, la base de datos está migrada y conectada, la web carga tras login y la conexión con el Channel Manager funciona en producción.

**Why this priority**: Da confianza de que el despliegue fue exitoso y permite detectar problemas antes de que el host los sufra. Es importante, pero secundario a tener la app arriba.

**Independent Test**: Ejecutar la lista de verificación (salud de la API, prueba de conexión al Channel Manager, carga de la web tras login) y obtener todos los chequeos en verde.

**Acceptance Scenarios**:

1. **Given** la app desplegada, **When** se consulta el chequeo de salud de la API, **Then** responde correctamente y de forma estable.
2. **Given** la app desplegada, **When** se ejecuta la prueba de conexión al Channel Manager, **Then** confirma la propiedad real del host.
3. **Given** la base de datos gestionada, **When** se verifica el esquema, **Then** está completo y al día (todas las migraciones aplicadas).

---

### Edge Cases

- **Secreto faltante**: si falta una credencial (Channel Manager, IA, búsqueda, contraseña de la web), el servicio afectado debe fallar de forma explícita y segura, sin exponer el valor de ningún secreto en logs ni respuestas.
- **Base de datos suspendida**: el proveedor gratuito de base de datos puede suspender la instancia por inactividad; la primera petición tras la suspensión debe reconectar sin intervención manual.
- **Origen no autorizado**: una web alojada en un dominio distinto al configurado no debe poder consumir la API (restricción de orígenes).
- **Token del Channel Manager caducado**: el token de corta duración debe renovarse automáticamente en producción sin que el operador intervenga.
- **Reinicio del servicio**: tras un reinicio, la app debe volver a estar sana sin pasos manuales (migraciones idempotentes, configuración desde el entorno).
- **Sobrecosto**: el consumo debe poder vigilarse para no exceder el presupuesto objetivo; un pico inesperado debe ser observable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La aplicación MUST estar disponible en una URL pública estable, accesible por HTTPS, sin requerir ejecución local.
- **FR-002**: La web MUST exigir autenticación por contraseña antes de mostrar cualquier dato o permitir acciones.
- **FR-003**: La API en producción MUST usar una base de datos Postgres gestionada y externa al servicio de cómputo, con conexión cifrada (SSL).
- **FR-004**: El esquema de la base de datos MUST aplicarse automáticamente (migraciones) al publicar una versión, de forma idempotente y segura ante reinicios.
- **FR-005**: Toda la configuración sensible (credenciales de IA, búsqueda, Channel Manager, contraseña de la web, clave de sesión, cadena de conexión) MUST provenir de variables de entorno del proveedor, NUNCA del repositorio.
- **FR-006**: La API MUST aceptar peticiones solo desde el dominio de la web configurado (orígenes restringidos).
- **FR-007**: La web MUST conocer la dirección pública de la API por configuración, sin valores embebidos en el código.
- **FR-008**: El sistema MUST publicarse de forma reproducible mediante artefactos versionados en el repositorio (no pasos manuales no documentados).
- **FR-009**: El proyecto MUST incluir una guía paso a paso para el operador que cubra: crear la base de datos gestionada, crear los servicios web y API, configurar variables, primer despliegue y verificación.
- **FR-010**: El sistema MUST exponer un chequeo de salud de la API verificable tras el despliegue que confirme tanto que el servicio responde (liveness) como que la conexión a la base de datos está operativa; si la base de datos no responde, el chequeo MUST reflejar el estado degradado.
- **FR-011**: El sistema MUST permitir verificar en producción la conexión con el Channel Manager (prueba que confirme la propiedad real).
- **FR-012**: Ningún secreto MUST aparecer en logs, mensajes de error o respuestas de la API.
- **FR-013**: El despliegue MUST mantenerse dentro de un presupuesto objetivo bajo (base de datos en tier gratuito; cómputo en un plan económico), y el consumo MUST ser observable por el operador.
- **FR-014**: La renovación de credenciales de corta duración del Channel Manager MUST ocurrir automáticamente en producción.
- **FR-015**: El proceso de actualización (nueva versión) MUST poder ejecutarse repetidamente sin pérdida de datos ni intervención manual fuera de la guía.
- **FR-016**: El sistema MUST ejecutar el escaneo de eventos/mercado de forma automática una vez al día mediante una tarea programada en el proveedor de cómputo, sin intervención del operador, y registrar el resultado de cada corrida.
- **FR-017**: El despliegue MUST publicarse de forma continua: un cambio integrado en la rama principal (`main`) MUST disparar automáticamente una nueva versión en producción (web y API), incluyendo la aplicación de migraciones.
- **FR-018**: La estrategia de recuperación ante pérdida de datos en v1 MUST basarse en re-importar el estado desde el Channel Manager (fuente de verdad de precios y reservas); no se exige un mecanismo de respaldo adicional, pero la re-importación MUST ser posible bajo demanda.

### Key Entities

- **Servicio Web**: la interfaz que usa el host; depende de la dirección pública de la API y de la contraseña de acceso.
- **Servicio API**: el backend que sirve datos y ejecuta acciones; depende de la base de datos gestionada y de las credenciales externas (IA, búsqueda, Channel Manager).
- **Base de datos gestionada**: almacén Postgres externo (tier gratuito), con conexión cifrada; fuente de verdad de propiedades, precios, reservas, sugerencias y auditoría.
- **Configuración de entorno**: conjunto de variables que parametrizan ambos servicios; incluye secretos y direcciones públicas.
- **Guía del operador**: documento reproducible con los pasos de despliegue y verificación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El host puede acceder a la app desde una URL pública e iniciar sesión en menos de 1 minuto, desde un dispositivo sin configuración previa.
- **SC-002**: Un operador, siguiendo solo la guía, lleva la app de cero a una URL pública funcional en menos de 60 minutos.
- **SC-003**: El 100% de las migraciones quedan aplicadas automáticamente tras el primer despliegue, verificable en la base de datos.
- **SC-004**: Tras el despliegue, el chequeo de salud de la API y la prueba de conexión al Channel Manager responden correctamente en producción.
- **SC-005**: Publicar una nueva versión (cambio menor) y verla reflejada en línea toma menos de 15 minutos y no requiere pasos manuales fuera de la guía.
- **SC-006**: El costo recurrente de infraestructura se mantiene en el rango objetivo (base de datos $0; cómputo en el orden de unos pocos dólares al mes para uso personal), y el operador puede consultar el consumo.
- **SC-007**: No existe ningún secreto en el repositorio ni en los logs; una revisión del historial y de la salida de los servicios no expone credenciales.
- **SC-008**: El escaneo de mercado se ejecuta automáticamente al menos una vez al día en producción, verificable por el registro de corridas (sin que el operador lo dispare).
- **SC-009**: El chequeo de salud refleja correctamente el estado de la base de datos: responde sano cuando la BD está conectada y degradado cuando no lo está.

## Assumptions

- **Single-tenant**: la app es de uso personal del host; no hay múltiples cuentas ni gestión de usuarios más allá de la contraseña única.
- **Proveedores**: cómputo en un plan económico de pago por uso y base de datos en un tier gratuito gestionado; la creación de cuentas, la facturación y la acción de "publicar" las realiza el operador, no el sistema.
- **Stack sin cambios**: se mantiene el stack actual (web y API ya existentes) y no se introduce un orquestador nuevo.
- **Contraseña ya existente**: el mecanismo de contraseña de la web ya está implementado y se reutiliza tal cual.
- **Channel Manager por API V2**: en producción se usa la integración V2 (token con renovación automática) ya construida; la V1 queda solo como lectura/diagnóstico.
- **Tareas programadas (escaneo de mercado)**: decidido — el escaneo de eventos corre automáticamente una vez al día mediante una tarea programada en el proveedor de cómputo (ver FR-016).
- **Despliegue continuo**: decidido — los cambios integrados en `main` se publican automáticamente (ver FR-017); no hay despliegues manuales en el flujo normal.
- **Recuperación de datos**: decidido — ante pérdida de datos se re-importa desde el Channel Manager (ver FR-018); v1 no incluye respaldos programados de la base de datos.
- **Dominio**: se acepta el dominio público que asigna el proveedor de cómputo; un dominio propio es opcional y fuera de alcance de v1.
- **Región/latencia**: se asume una región estándar; la optimización de latencia geográfica está fuera de alcance.
