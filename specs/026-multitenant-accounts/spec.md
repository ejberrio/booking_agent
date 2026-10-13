# Feature Specification: Multicliente mínimo — cuentas, registro y datos aislados

**Feature Branch**: `026-multitenant-accounts`
**Created**: 2026-10-10
**Status**: Draft
**Input**: User description: "Multicliente mínimo — cuentas, registro y datos aislados (issue #143, Feature 026, épica #156 Comercial Fase 0)."

## Contexto

StayLever es hoy una herramienta personal: **un solo anfitrión** entra con una **contraseña única compartida**, la sesión no identifica a nadie y casi toda la información y la configuración (conexión con el channel manager, credenciales, preferencias, chat, avisos al celular, etc.) es global. Para la fase comercial (épica #156) varios anfitriones con 1–5 apartamentos deben poder usarla, **cada uno con su cuenta y sus datos aislados**. Esta feature es la base de todas las demás de la fase.

Decisiones del host (2026-10-10):

1. Durante la beta **solo se entra con código de invitación** que el administrador de plataforma (el host actual) genera desde un panel. Un **interruptor** permitirá abrir el registro más adelante.
2. Inicio de sesión con **correo y contraseña** (con verificación de correo y "olvidé mi contraseña") **y también "Entrar con Google"**.
3. **Un solo usuario por cuenta** en esta versión; el modelo queda preparado para varios.

Principios que rigen (constitución v1.1.0): **VI. Aislamiento por cuenta (NO NEGOCIABLE)** y **III. Human-in-the-loop** para toda escritura en los canales. El repositorio es público: ninguna credencial en el código.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El host actual reclama su cuenta sin perder nada (Priority: P1)

Como host actual quiero que, tras el cambio, todo lo que tengo hoy (propiedad, precios, reservas, sugerencias, promociones, notas, historial y auditoría, chat, teléfono registrado para avisos, preferencias y conexión con Beds24) quede en **mi cuenta**, y entrar con mi correo en lugar de la contraseña compartida.

**Why this priority**: sin esto el host pierde su herramienta; es la condición para desplegar la feature.

**Independent Test**: desplegar sobre una copia de los datos de producción, entrar por primera vez con la contraseña actual, crear el usuario dueño con correo y contraseña, y comprobar que cada pantalla muestra exactamente lo mismo que antes (mismos conteos de precios, reservas, sugerencias, conversaciones y teléfonos).

**Acceptance Scenarios**:

1. **Given** el sistema recién actualizado y la cuenta nº 1 sin usuario, **When** el host entra con la contraseña compartida actual, **Then** se le pide crear su usuario dueño (correo y contraseña) y, al verificar el correo, entra a su cuenta con todos sus datos.
2. **Given** la cuenta nº 1 ya reclamada, **When** alguien intenta entrar con la contraseña compartida, **Then** no se acepta; solo se entra con correo/contraseña o Google.
3. **Given** la cuenta reclamada, **When** el host usa calendario, sugerencias, ofertas, chat, ajustes y avisos, **Then** todo funciona igual que antes y los avisos siguen llegando al mismo teléfono sin reinstalar la app.
4. **Given** el usuario del host, **Then** tiene además el rol de **administrador de plataforma**.

---

### User Story 2 - Un anfitrión nuevo crea su cuenta con un código de invitación (Priority: P1)

Como anfitrión invitado quiero crear mi cuenta con el código que me dieron, usando mi correo o mi cuenta de Google, y entrar a una StayLever vacía que me explique qué sigue.

**Why this priority**: es el objetivo de la fase 0 (recibir anfitriones beta).

**Independent Test**: generar un código en el panel de administrador, registrarse con él (una vez con correo y otra con Google), verificar el correo y entrar: la app aparece vacía, con un mensaje claro de cómo conectar su channel manager, y sin rastro de los datos del host.

**Acceptance Scenarios**:

1. **Given** un código de invitación vigente y el registro cerrado, **When** el anfitrión se registra con nombre, correo, contraseña y el código, **Then** se crea su cuenta, recibe un correo de verificación y, al confirmarlo, entra a su cuenta.
2. **Given** un código vigente, **When** elige "Entrar con Google" e ingresa el código, **Then** se crea su cuenta con el correo de Google (ya verificado) y entra.
3. **Given** un código ya usado, vencido o revocado, **When** intenta registrarse, **Then** ve un mensaje claro y no se crea nada.
4. **Given** el registro cerrado y sin código, **When** intenta registrarse, **Then** se le indica que StayLever está en beta por invitación.
5. **Given** una cuenta nueva sin channel manager conectado, **When** entra, **Then** ve las pantallas vacías con un mensaje que explica cómo conectarse (Ajustes) y ninguna acción falla con errores técnicos.
6. **Given** una cuenta nueva, **When** pega en Ajustes un código de invitación de **su** Beds24 (como hace hoy el host), **Then** su propiedad y su calendario se importan **solo a su cuenta**.

---

### User Story 3 - Cada cuenta ve y modifica solo lo suyo (Priority: P1)

Como anfitrión quiero tener la certeza de que nadie más ve mis precios, reservas, conversaciones ni credenciales, y de que nada de lo que hagan otros anfitriones (ni el agente de otra cuenta) puede tocar mis datos ni mis canales.

**Why this priority**: es el principio VI (no negociable); un fallo aquí destruye la confianza y expone credenciales.

**Independent Test**: con dos cuentas con datos, recorrer todas las pantallas y operaciones con la cuenta B (incluido el chat del agente pidiendo explícitamente datos o cambios de la unidad de A) y comprobar que nunca aparece ni cambia nada de A; repetir para avisos al celular, avisos entrantes de Beds24 y tareas programadas.

**Acceptance Scenarios**:

1. **Given** las cuentas A y B, **When** B consulta calendario, reservas, sugerencias, promociones, notas, historial, chat, teléfonos, ajustes o estado, **Then** solo ve datos de B.
2. **Given** B conoce el identificador de una unidad, sugerencia, promoción o conversación de A, **When** intenta verla o modificarla (por pantalla, enlace directo o pidiéndoselo al agente), **Then** el sistema responde como si no existiera y no se escribe nada en ningún canal.
3. **Given** una reserva nueva de la propiedad de A, **When** llega el aviso entrante de Beds24, **Then** se registra solo en A y solo los teléfonos de A reciben el aviso.
4. **Given** un aviso entrante con una clave que no pertenece a ninguna cuenta, **Then** se rechaza y no modifica nada.
5. **Given** el escaneo diario, **When** corre, **Then** produce sugerencias para cada cuenta con su propia propiedad y ciudad, y los avisos de sugerencias van solo a los teléfonos de cada cuenta.
6. **Given** la auditoría de cambios, **Then** cada registro indica la cuenta y el usuario que hizo el cambio (o "sistema"/"agente" con el usuario que lo confirmó).

---

### User Story 4 - Entrar, salir y recuperar el acceso (Priority: P2)

Como usuario quiero iniciar sesión con correo/contraseña o Google (en la web y en la app de Android), recuperar mi contraseña si la olvido y cerrar mis sesiones en todos los dispositivos si pierdo el teléfono.

**Why this priority**: necesario para operar con varios usuarios reales, pero el host puede vivir unos días sin "olvidé mi contraseña".

**Independent Test**: entrar con correo, con Google y desde la app de Android; pedir recuperación de contraseña y cambiarla; usar "cerrar todas mis sesiones" y comprobar que los demás dispositivos quedan fuera.

**Acceptance Scenarios**:

1. **Given** un usuario verificado, **When** entra con correo y contraseña correctos, **Then** accede a su cuenta; la sesión dura 7 días en la web y 90 días en la app móvil.
2. **Given** credenciales incorrectas, **Then** ve un mensaje genérico (sin revelar si el correo existe) y, tras varios intentos fallidos seguidos, debe esperar antes de reintentar.
3. **Given** "olvidé mi contraseña", **When** ingresa su correo, **Then** recibe (si existe) un enlace de un solo uso y de corta duración para fijar una nueva; al cambiarla, se cierran sus demás sesiones.
4. **Given** "cerrar sesión", **Then** esa sesión deja de servir en el servidor (no solo se borra del navegador); **Given** "cerrar todas mis sesiones", **Then** todas sus sesiones dejan de servir.
5. **Given** un usuario registrado con correo, **When** usa "Entrar con Google" con el mismo correo verificado, **Then** entra a su misma cuenta (no se crea otra).
6. **Given** la app de Android instalada, **When** el usuario entra con Google, **Then** el flujo funciona dentro de la app (no queda bloqueado por la pantalla de Google).

---

### User Story 5 - Panel del administrador de plataforma (Priority: P2)

Como administrador de plataforma (el host) quiero crear y revocar códigos de invitación, ver las cuentas, desactivarlas o reactivarlas, abrir o cerrar el registro y gestionar los secretos de la plataforma, sin ver los datos privados de cada cuenta.

**Why this priority**: controla quién entra a la beta y el costo; se puede operar unos días creando códigos a mano, pero no mucho.

**Independent Test**: crear un código con una nota ("Ana, Cartagena"), verlo como "sin usar", registrarse con él, verlo "usado por la cuenta X"; desactivar la cuenta X y comprobar que su usuario no puede entrar y que el escaneo la omite; reactivarla.

**Acceptance Scenarios**:

1. **Given** el panel, **When** crea un código, **Then** obtiene un código para compartir, con fecha de vencimiento (por defecto 30 días) y una nota opcional; puede revocarlo mientras no se use.
2. **Given** el panel, **Then** ve la lista de cuentas con nombre, correo del dueño, fecha de creación, último acceso, si tiene channel manager conectado y nº de propiedades — **sin** precios, reservas ni conversaciones.
3. **Given** una cuenta desactivada, **Then** sus usuarios no pueden entrar (mensaje claro), sus sesiones se cierran y las tareas programadas la omiten; sus datos se conservan y al reactivarla todo vuelve.
4. **Given** el interruptor de registro abierto encendido, **Then** cualquiera puede registrarse sin código; apagado, solo con código.
5. **Given** los secretos de plataforma (claves de IA, búsqueda, avisos al celular, correo, Google), **Then** solo el administrador de plataforma los ve y cambia; los demás usuarios solo ven los de su cuenta (Beds24).
6. **Given** un usuario que no es administrador, **When** intenta abrir el panel, **Then** no tiene acceso.

---

### User Story 6 - Cada cuenta con su ciudad (Priority: P3)

Como anfitrión de Bogotá o Cartagena quiero que los eventos, el mercado y las sugerencias se basen en **mi ciudad**, no en Medellín.

**Why this priority**: los anfitriones beta pueden estar en otras ciudades; sin esto sus sugerencias serían erróneas, aunque la cuenta funcione.

**Independent Test**: con una cuenta cuya propiedad está en Cartagena, correr el escaneo y comprobar que los eventos y referencias de mercado son de Cartagena y que la cuenta de Medellín no cambia.

**Acceptance Scenarios**:

1. **Given** una propiedad en Cartagena, **When** corre el escaneo, **Then** se buscan eventos y mercado de Cartagena y las sugerencias de esa cuenta los usan.
2. **Given** dos cuentas en la misma ciudad, **Then** los eventos de esa ciudad se buscan una sola vez y ambas los aprovechan (datos públicos compartidos).
3. **Given** el agente de una cuenta, **Then** habla de la ciudad y la moneda de la propiedad de esa cuenta.

---

### Edge Cases

- **Correo ya registrado**: registrarse con un correo existente no crea otra cuenta; se ofrece entrar o recuperar la contraseña (sin revelar a terceros si el correo existe).
- **Correo sin verificar**: no puede usar la app hasta verificarlo; puede pedir reenviar el correo; el enlace vence (24 h).
- **Código de invitación usado dos veces a la vez**: solo uno de los registros lo consume; el otro recibe "código ya usado".
- **Google con correo distinto al registrado**: crea un usuario nuevo (y requiere código si el registro está cerrado); no se vinculan cuentas por coincidencias parciales.
- **Cuenta sin channel manager**: el escaneo diario, la sincronización y los avisos la omiten sin error; las pantallas muestran estado vacío.
- **Credencial de Beds24 de una cuenta caducada**: solo esa cuenta muestra "conexión perdida"; las demás siguen.
- **Dos cuentas conectan la misma propiedad de Beds24**: se impide; una propiedad del channel manager pertenece a una sola cuenta (mensaje claro a la segunda).
- **Cuenta desactivada durante una sesión abierta**: la siguiente acción la saca con un mensaje claro.
- **Escritura pendiente de confirmación en el chat cuando se desactiva la cuenta o se cierra la sesión**: no se ejecuta.
- **El administrador de plataforma**: es un rol del usuario, no da acceso a los datos privados de otras cuentas desde la app.
- **Migración repetida o fallida**: si la actualización falla a mitad, no se pierde ni se duplica nada; puede reintentarse.
- **Contraseña compartida antigua en dispositivos con sesión vieja**: tras la actualización, las sesiones antiguas dejan de valer y piden entrar de nuevo (la app móvil incluida), sin perder los avisos.

## Requirements *(mandatory)*

### Functional Requirements

**Cuentas y usuarios**

- **FR-001**: El sistema MUST organizar la información en **cuentas**; cada cuenta tiene un nombre y un usuario dueño, y el modelo MUST permitir más de un usuario por cuenta en el futuro sin rehacer los datos.
- **FR-002**: Cada usuario MUST tener un correo único en todo el sistema, nombre y, opcionalmente, contraseña y/o identidad de Google.
- **FR-003**: El sistema MUST distinguir el rol **administrador de plataforma** (asignado al usuario del host) del usuario normal.

**Registro y acceso**

- **FR-004**: Con el registro cerrado, crear una cuenta MUST requerir un **código de invitación** vigente; con el registro abierto, no.
- **FR-005**: Los códigos de invitación MUST ser de un solo uso, con vencimiento (30 días por defecto), nota opcional y revocables mientras no se usen; MUST registrar qué cuenta los usó.
- **FR-006**: El registro con correo MUST pedir nombre, correo y contraseña (mínimo 10 caracteres, rechazando contraseñas muy comunes) y MUST enviar un correo de verificación con enlace de un solo uso válido 24 h; sin verificar no se usa la app.
- **FR-007**: El sistema MUST permitir **"Entrar con Google"** para registrarse (con código si el registro está cerrado) y para entrar; un correo de Google verificado igual al de un usuario existente MUST entrar a ese usuario.
- **FR-008**: Las contraseñas MUST guardarse de forma que no puedan recuperarse (solo verificarse); los mensajes de error de acceso MUST ser genéricos y MUST limitarse los intentos fallidos repetidos por correo y por origen.
- **FR-009**: El sistema MUST ofrecer **recuperación de contraseña** por correo con enlace de un solo uso válido 1 h; al cambiar la contraseña se MUST cerrar las demás sesiones del usuario.
- **FR-010**: Las sesiones MUST poder invalidarse en el servidor: "cerrar sesión" invalida la actual y "cerrar todas mis sesiones" todas las del usuario; duración 7 días en web y 90 días en la app móvil (como hoy).
- **FR-011**: Usuarios de una cuenta desactivada MUST no poder entrar y sus sesiones MUST dejar de valer.
- **FR-012**: La app de Android MUST seguir funcionando: entrar con correo sin reinstalar; entrar con Google funcionando dentro de la app (si eso exige publicar una nueva versión del APK, se publica como parte de esta feature).

**Aislamiento (principio VI)**

- **FR-013**: Todo dato del anfitrión MUST pertenecer a exactamente una cuenta: propiedades y unidades, calendario, tarifas, disponibilidad, reservas, sugerencias, promociones y ofertas, ajustes por canal, ofertas nativas, notas del calendario, historial y auditoría, conversaciones y acciones del agente, teléfonos y registro de avisos, preferencias, configuración del escaneo, puntos de interés, registros e incidencias de sincronización, avisos entrantes, conexión y credenciales del channel manager, clave del aviso entrante.
- **FR-014**: La cuenta de cada operación MUST derivarse de la sesión autenticada (o de la clave del aviso entrante / de la tarea programada que recorre las cuentas), nunca de un dato enviado por el navegador ni elegido por el agente.
- **FR-015**: Cualquier intento de leer o modificar un dato de otra cuenta MUST comportarse como "no existe" y MUST no escribir nada en ningún canal.
- **FR-016**: Las herramientas del agente MUST operar solo sobre las unidades de la cuenta de la conversación; el contexto que recibe el agente MUST contener solo datos de esa cuenta; las escrituras siguen requiriendo confirmación del usuario de esa cuenta (principio III).
- **FR-017**: La auditoría MUST registrar cuenta y usuario de cada cambio.
- **FR-018**: Los datos públicos (eventos de una ciudad, referencias de mercado de una zona) MAY compartirse entre cuentas; MUST no contener datos privados de ninguna cuenta.
- **FR-019**: El servicio interno que guarda los datos MUST rechazar toda petición que no venga con una identidad válida emitida por StayLever (hoy acepta cualquiera que llegue por la red interna).

**Channel manager por cuenta**

- **FR-020**: Cada cuenta MUST tener su propia conexión con el channel manager (credencial, propiedades y unidades importadas, clave del aviso entrante); la conexión del host actual MUST migrarse a la cuenta nº 1.
- **FR-021**: Conectar Beds24 pegando un código de invitación en Ajustes (como hoy) MUST funcionar para cualquier cuenta e importar sus propiedades **solo** a esa cuenta.
- **FR-022**: Una misma propiedad del channel manager MUST no poder pertenecer a dos cuentas.
- **FR-023**: Los avisos entrantes de Beds24 MUST identificar la cuenta por su clave; claves desconocidas MUST rechazarse; la URL/clave a configurar en Beds24 MUST mostrarse por cuenta en Ajustes.

**Tareas programadas y avisos**

- **FR-024**: La sincronización y el escaneo diario (eventos, mercado, sugerencias) MUST recorrer todas las cuentas **activas con channel manager conectado**; el fallo de una cuenta MUST quedar registrado en esa cuenta y no detener las demás.
- **FR-025**: Los eventos y el mercado MUST buscarse por la ciudad/zona de la propiedad de cada cuenta; una ciudad compartida por varias cuentas MUST buscarse una sola vez por escaneo.
- **FR-026**: Los avisos al celular MUST enviarse solo a los teléfonos de la cuenta afectada; el teléfono ya registrado del host MUST pasar a su cuenta.
- **FR-027**: Los textos del agente y de los avisos MUST usar la ciudad y la moneda de la propiedad de la cuenta (la beta sigue siendo Colombia/COP, pero sin "Medellín" fijo).

**Administración de plataforma**

- **FR-028**: El panel de administrador MUST permitir: crear, listar y revocar códigos de invitación; listar cuentas con datos no privados (nombre, correo del dueño, alta, último acceso, conexión sí/no, nº de propiedades); desactivar y reactivar cuentas; activar/desactivar el registro abierto.
- **FR-029**: Los secretos se MUST separar en **de plataforma** (IA, búsqueda, avisos, correo, Google; solo el administrador) y **de cuenta** (Beds24; solo esa cuenta). La configuración del modelo de IA es de plataforma.

**Migración**

- **FR-030**: Al actualizar, todos los datos existentes MUST quedar en la **cuenta nº 1** sin pérdida ni duplicados; el proceso MUST poder reintentarse si falla.
- **FR-031**: Mientras la cuenta nº 1 no tenga usuario, la contraseña compartida actual MUST servir **solo** para crear su usuario dueño (que recibe el rol de administrador de plataforma); después MUST dejar de aceptarse.

**Idiomas y apariencia**

- **FR-032**: Todas las pantallas y correos nuevos (registro, verificación, recuperación, panel) MUST estar en es/en/pt y respetar el tema claro/oscuro; los correos usan el idioma elegido por el usuario (por defecto el del navegador).

### Key Entities

- **Cuenta**: el espacio de un anfitrión; nombre, estado (activa/desactivada), fecha de alta, último acceso. Dueña de todos los datos del anfitrión.
- **Usuario**: persona que entra; correo (único), nombre, contraseña opcional, identidad de Google opcional, correo verificado sí/no, idioma, rol de administrador de plataforma sí/no.
- **Membresía**: relación usuario–cuenta con su rol en la cuenta (hoy siempre "dueño"); prepara varios usuarios por cuenta.
- **Sesión**: acceso vigente de un usuario desde un dispositivo; tipo (web/app), creación, vencimiento, último uso; revocable.
- **Código de invitación**: código, nota, vencimiento, estado (vigente/usado/vencido/revocado), cuenta que lo usó.
- **Enlace de un solo uso**: para verificar correo o recuperar contraseña; propósito, vencimiento, usado sí/no.
- **Ajustes de plataforma**: registro abierto sí/no y secretos de plataforma.
- **Conexión del channel manager**: por cuenta; proveedor, credencial (cifrada), clave del aviso entrante, estado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tras la actualización, el host reclama su cuenta en menos de 3 minutos y el 100 % de sus datos (precios, reservas, sugerencias, promociones, notas, conversaciones, teléfonos, auditoría) aparece igual que antes (conteos idénticos antes/después).
- **SC-002**: Un anfitrión invitado crea su cuenta y entra en menos de 5 minutos, con correo o con Google, desde la web o desde la app de Android.
- **SC-003**: En las pruebas de aislamiento con dos cuentas, **0** datos de una cuenta son visibles o modificables desde la otra, cubriendo el 100 % de las pantallas, operaciones, herramientas del agente, avisos al celular, avisos entrantes y tareas programadas.
- **SC-004**: "Cerrar todas mis sesiones" y desactivar una cuenta dejan fuera a todos los dispositivos de ese usuario/cuenta en su siguiente acción (≤ 1 minuto).
- **SC-005**: Con 3 cuentas activas, una de ellas con la conexión rota, el escaneo diario termina para las otras 2 y la rota queda marcada solo en su cuenta.
- **SC-006**: Todas las pruebas existentes siguen pasando y se añaden pruebas de aislamiento para cada tipo de dato de FR-013.
- **SC-007**: Después de 10 intentos fallidos seguidos de acceso a un mismo correo, los siguientes se bloquean temporalmente (al menos 15 minutos).

## Assumptions

- Beta en Colombia: la moneda sigue siendo COP y el huso horario Colombia; FR-027 evita "Medellín" fijo pero la generalización completa de moneda/huso queda para cuando haya anfitriones fuera de Colombia.
- El envío de correos (verificación, recuperación) usa un servicio de correo transaccional que el host configura con el dominio staylever.com; "Entrar con Google" usa credenciales de Google que el host crea. Ambos son secretos de plataforma que el host carga (nunca en el repositorio).
- Google bloquea su inicio de sesión dentro de vistas web embebidas; en la app de Android el flujo de Google se hace por el navegador del sistema o un mecanismo nativo, lo que puede requerir publicar una nueva versión del APK (1.1.0).
- Las sesiones antiguas (firmadas con la contraseña compartida) se invalidan al actualizar: el host y su app deben entrar una vez con el nuevo acceso; el teléfono sigue registrado para avisos.
- Los datos públicos compartidos son: eventos por ciudad y referencias de mercado por zona. Los puntos de interés son de cada cuenta (dependen de la ubicación del apartamento).
- El administrador de plataforma no navega los datos privados de otras cuentas desde la app; el soporte que lo requiera queda fuera de esta feature.
- Un solo usuario por cuenta; invitar usuarios adicionales a una cuenta, planes/cobro (#152), límites de IA (#144), privacidad y política de datos (#145), modo sin conexión (#146), página pública (#147) y el asistente de conexión de Beds24 (#150) quedan fuera.
- Escala esperada de la beta: decenas de cuentas, cada una con 1–5 apartamentos; no se requiere infraestructura separada por cuenta.
