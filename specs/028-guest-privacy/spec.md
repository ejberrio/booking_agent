# Feature Specification: Privacidad de huéspedes y política de datos (Ley 1581)

**Feature Branch**: `028-guest-privacy`
**Created**: 2026-10-14
**Status**: Draft
**Input**: Issue #145 (Feature 028, épica #156 Comercial Fase 0). StayLever ya es multicliente (feature 026). Del huésped solo se guarda el nombre que llega del channel manager; el anfitrión debe seguir viéndolo, el administrador de plataforma nunca. Conservar el nombre hasta 1 año tras la salida; aceptación obligatoria y versionada de Términos y Privacidad; derechos de acceso (exportar) y supresión (borrar la cuenta); Términos que fijan a StayLever como Encargado; inventario interno de datos.

## Contexto

- Bajo la Ley 1581 de 2012, el **anfitrión es el Responsable** de los datos de sus huéspedes (los recibe de Booking, Airbnb o su channel manager) y **StayLever es el Encargado**: los trata por cuenta del anfitrión y solo para prestarle el servicio.
- Hoy StayLever guarda del huésped **únicamente el nombre** (sin teléfono, correo ni documento). El nombre ya se ve solo dentro de la cuenta del anfitrión y nunca va a registros técnicos, avisos al celular ni a la IA.
- Hay páginas públicas de presentación y de privacidad; faltan los Términos de uso, la aceptación registrada y las herramientas para ejercer los derechos del titular.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aceptar Términos y Privacidad (Priority: P1)

Un anfitrión que crea su cuenta (con correo o con Google) debe marcar una casilla obligatoria "Acepto los Términos de uso y la Política de privacidad", con enlaces a ambos documentos. StayLever registra qué versión aceptó y cuándo. Quien ya tiene cuenta (incluido el administrador) ve, la próxima vez que entra, una pantalla para aceptarlos antes de seguir; lo mismo ocurre cuando se publica una versión nueva.

**Why this priority**: es la base legal para tratar datos (autorización del titular y contrato de encargo con el anfitrión). Sin esto no se pueden recibir anfitriones beta.

**Independent Test**: crear una cuenta sin marcar la casilla (no deja), marcándola (queda registrada la versión y la fecha); entrar con un usuario existente y comprobar que no puede usar la app hasta aceptar; publicar una versión nueva y comprobar que se vuelve a pedir.

**Acceptance Scenarios**:

1. **Given** el formulario de registro, **When** el anfitrión intenta crear la cuenta sin marcar la casilla, **Then** no se crea y se le indica que debe aceptar.
2. **Given** el registro con Google, **When** el anfitrión no ha aceptado, **Then** antes de ir a Google debe marcar la casilla; al volver, su aceptación queda registrada.
3. **Given** un usuario existente sin aceptación vigente, **When** entra (web o app), **Then** ve la pantalla de aceptación y ninguna otra función de la app responde hasta que acepta.
4. **Given** un usuario que aceptó la versión vigente, **When** el administrador publica una versión nueva, **Then** en su siguiente acceso se le pide aceptar de nuevo, y se conserva el historial de aceptaciones.
5. **Given** cualquier visitante, **When** abre los Términos o la Privacidad desde el pie de página, la entrada o el registro, **Then** los lee sin necesidad de cuenta, en es/en/pt.

---

### User Story 2 - Nombre del huésped visible solo para el anfitrión y borrado tras 1 año (Priority: P1)

El anfitrión sigue viendo quién tiene cada reserva, como en Booking o Airbnb. Nadie más lo ve: ni otras cuentas ni el administrador de plataforma (panel, descargas o registros técnicos). Cuando pasa 1 año desde la fecha de salida, StayLever borra el nombre automáticamente; la reserva se conserva (fechas, precio, canal y estado) para las estadísticas de precios.

**Why this priority**: es el dato personal que hoy se guarda; limitar su vida útil y su visibilidad es el núcleo de la feature.

**Independent Test**: con reservas de salida hace 13 meses y hace 11 meses, correr la limpieza diaria y comprobar que solo la primera pierde el nombre y que ambas siguen existiendo con sus demás datos; comprobar que el administrador no ve nombres en ninguna pantalla ni descarga.

**Acceptance Scenarios**:

1. **Given** una reserva con salida hace más de 1 año, **When** corre la limpieza diaria, **Then** el nombre del huésped queda vacío y la reserva sigue contando en calendario, ocupación y estadísticas.
2. **Given** una reserva con salida hace menos de 1 año, **When** corre la limpieza, **Then** conserva el nombre.
3. **Given** una reserva antigua (salida hace más de 1 año) que el channel manager vuelve a enviar, **When** se importa, **Then** no se guarda su nombre.
4. **Given** el administrador de plataforma, **When** revisa el panel de cuentas o cualquier vista de plataforma, **Then** no ve nombres de huéspedes de ninguna cuenta.
5. **Given** la limpieza diaria, **When** falla en una cuenta, **Then** las demás cuentas se procesan igual y el fallo queda registrado sin datos personales.

---

### User Story 3 - Descargar una copia de mis datos (Priority: P2)

Desde Ajustes, el dueño de la cuenta descarga un archivo con todos los datos de su cuenta: su usuario, propiedades, calendario, tarifas, reservas (con nombres de huéspedes vigentes), sugerencias, conversaciones con el asistente, preferencias y registros de cambios. No incluye contraseñas, credenciales del channel manager ni claves.

**Why this priority**: cumple el derecho de acceso del titular y da confianza; no bloquea a los demás.

**Independent Test**: descargar la copia de una cuenta con datos y verificar que contiene sus datos, ninguno de otra cuenta y ningún secreto.

**Acceptance Scenarios**:

1. **Given** el dueño de una cuenta con propiedades y reservas, **When** pide la copia, **Then** recibe un archivo legible por máquina con todos sus datos en menos de 1 minuto.
2. **Given** dos cuentas, **When** una descarga su copia, **Then** el archivo no contiene ningún dato de la otra.
3. **Given** la copia descargada, **When** se revisa, **Then** no hay contraseñas, tokens, claves ni credenciales del channel manager.

---

### User Story 4 - Borrar mi cuenta y todos sus datos (Priority: P2)

Desde Ajustes, el dueño borra su cuenta. Debe escribir el nombre de la cuenta y confirmar su identidad (su contraseña o, si entra solo con Google, un código que se le envía por correo). StayLever borra todos los datos de la cuenta, cierra sus sesiones, desconecta sus teléfonos de los avisos y le confirma por correo. La cuenta principal del administrador no se puede borrar desde ahí.

**Why this priority**: cumple el derecho de supresión; se usa poco pero debe existir antes de recibir anfitriones.

**Independent Test**: borrar una cuenta de prueba con datos y verificar que no queda ningún registro suyo, que sus sesiones dejan de valer y que las demás cuentas no se afectan.

**Acceptance Scenarios**:

1. **Given** el dueño en Ajustes, **When** escribe mal el nombre de la cuenta o falla la confirmación de identidad, **Then** no se borra nada.
2. **Given** la confirmación correcta, **When** se borra la cuenta, **Then** desaparecen todos sus datos (usuario, propiedades, reservas, sugerencias, conversaciones, preferencias, avisos, credenciales, registros de cambios), sus sesiones dejan de valer y recibe un correo de confirmación.
3. **Given** otras cuentas, **When** se borra una, **Then** sus datos no cambian, y los datos públicos compartidos (eventos de la ciudad) se conservan.
4. **Given** la cuenta principal del administrador, **When** su dueño intenta borrarla, **Then** se le indica que no es posible desde ahí.
5. **Given** un código de invitación usado por la cuenta borrada, **When** el administrador revisa las invitaciones, **Then** la invitación figura como usada por una cuenta eliminada, sin datos personales.

---

### User Story 5 - Política de privacidad, Términos e inventario de datos al día (Priority: P3)

La Política de privacidad pública explica la retención de 1 año de los nombres de huéspedes y el rol de Encargado; los Términos de uso (nuevos) fijan el encargo, el uso aceptable, que es una beta sin garantías, la limitación de responsabilidad y la terminación. Internamente existe un inventario de datos: qué se guarda, dónde, para qué, con quién se comparte y por cuánto tiempo, incluido que las copias de seguridad se borran solas en máximo 7 días.

**Why this priority**: necesario para la beta, pero es contenido; se apoya en las historias anteriores.

**Independent Test**: leer /privacy y /terms en es/en/pt y comprobar que dicen lo que el producto hace; contrastar el inventario con lo que realmente se guarda.

**Acceptance Scenarios**:

1. **Given** /privacy, **When** se lee, **Then** indica la retención de 1 año del nombre del huésped, el rol de Encargado, los derechos de acceso y supresión desde Ajustes y el contacto privacy@staylever.com.
2. **Given** /terms, **When** se lee, **Then** incluye encargo del tratamiento, uso aceptable, beta sin garantías, limitación de responsabilidad, terminación y versión vigente.

---

### Edge Cases

- Un usuario acepta en la web y luego abre la app: no se le vuelve a pedir (la aceptación es por usuario, no por dispositivo).
- El registro con Google llega sin aceptación previa (por ejemplo, entrando por "Entrar con Google" con una invitación): se le pide aceptar antes de usar la app.
- La descarga de la copia de una cuenta grande no debe bloquear la app ni exceder un tiempo razonable.
- Se pide borrar la cuenta mientras corre la sincronización o el escaneo diario de esa cuenta: el borrado prevalece y el proceso de esa cuenta termina sin error para las demás.
- Una reserva sin fecha de salida válida no se anonimiza por error ni rompe la limpieza.
- La limpieza encuentra nombres ya vacíos: no hace nada.
- El dueño de la cuenta borrada intenta entrar de nuevo con el mismo correo: no existe; puede registrarse otra vez solo con una invitación nueva (o con el registro abierto).
- El código de confirmación por correo para borrar vence o se reusa: se rechaza.

## Requirements *(mandatory)*

### Functional Requirements

**Aceptación de documentos**

- **FR-001**: El registro (correo y Google) MUST exigir una casilla de aceptación de los Términos de uso y la Política de privacidad, con enlaces a ambos.
- **FR-002**: El sistema MUST guardar cada aceptación con el usuario, la versión de los documentos, la fecha y hora, y conservar el historial.
- **FR-003**: Un usuario sin aceptación de la versión vigente MUST ver una pantalla de aceptación al entrar (web y app) y no MUST poder usar ninguna otra función hasta aceptar; el servidor MUST imponerlo, no solo la interfaz.
- **FR-004**: El sistema MUST permitir publicar una versión nueva de los documentos, tras lo cual todos los usuarios deben aceptarla de nuevo.
- **FR-005**: /terms y /privacy MUST ser públicas, en es/en/pt, y estar enlazadas desde el pie de página, la entrada y el registro.

**Nombre del huésped**

- **FR-006**: Del huésped el sistema MUST guardar como máximo el nombre; MUST NOT guardar teléfono, correo, documento ni dirección.
- **FR-007**: El nombre MUST ser visible solo para los usuarios de la cuenta dueña de la reserva; MUST NOT aparecer en vistas, descargas ni registros del administrador de plataforma, ni en registros técnicos, avisos al celular o mensajes a la IA.
- **FR-008**: Una tarea diaria MUST borrar el nombre de las reservas cuya salida fue hace más de 365 días, en todas las cuentas activas, conservando el resto de la reserva; los fallos de una cuenta no MUST afectar a las demás.
- **FR-009**: Al importar una reserva cuya salida fue hace más de 365 días, el sistema MUST NOT guardar su nombre.

**Derecho de acceso**

- **FR-010**: El dueño de la cuenta MUST poder descargar desde Ajustes una copia de todos los datos de su cuenta en un formato legible por máquina.
- **FR-011**: La copia MUST incluir solo datos de esa cuenta y MUST excluir contraseñas, tokens, claves y credenciales.

**Derecho de supresión**

- **FR-012**: El dueño MUST poder borrar su cuenta desde Ajustes tras escribir el nombre de la cuenta y confirmar su identidad (contraseña; o código de un solo uso por correo, válido 15 minutos, si no tiene contraseña).
- **FR-013**: El borrado MUST eliminar todos los datos propios de la cuenta, revocar sus sesiones, desactivar sus teléfonos de avisos y enviar un correo de confirmación; MUST conservar los datos públicos compartidos.
- **FR-014**: La cuenta principal del administrador de plataforma MUST NOT poder borrarse con esta función.
- **FR-015**: El borrado MUST quedar registrado sin datos personales (qué cuenta por número y cuándo), visible para el administrador.

**Documentación**

- **FR-016**: /privacy MUST describir la retención de 1 año, el rol de Encargado, los derechos y cómo ejercerlos desde Ajustes, y las copias de seguridad que se borran solas en máximo 7 días.
- **FR-017**: /terms MUST incluir el encargo del tratamiento (anfitrión Responsable, StayLever Encargado), uso aceptable, beta sin garantías, limitación de responsabilidad, terminación y la versión vigente.
- **FR-018**: El repositorio MUST incluir un inventario interno de datos (qué, dónde, para qué, con quién se comparte, cuánto tiempo).

### Key Entities

- **Versión de documentos legales**: identificador de la versión vigente de Términos y Privacidad y su fecha de publicación.
- **Aceptación**: usuario, versión aceptada, fecha y hora; se conserva el historial.
- **Reserva**: ya existe; su nombre de huésped pasa a tener vida limitada (1 año tras la salida).
- **Registro de supresión**: número de la cuenta borrada y fecha, sin datos personales.
- **Código de confirmación de borrado**: un solo uso, 15 minutos, para usuarios sin contraseña.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las cuentas nuevas y de los usuarios activos tienen registrada la aceptación de la versión vigente antes de usar la app.
- **SC-002**: 0 nombres de huésped con salida de hace más de 1 año y 2 días en cualquier cuenta (la limpieza corre a diario).
- **SC-003**: 0 nombres de huéspedes visibles para el administrador de plataforma en cualquier pantalla, descarga o registro técnico (verificado por pruebas automáticas).
- **SC-004**: Un dueño descarga la copia completa de su cuenta en menos de 1 minuto.
- **SC-005**: Tras borrar una cuenta no queda ningún registro propio de ella (verificado por prueba automática sobre todas las tablas de datos de cuenta), y las demás cuentas no cambian.
- **SC-006**: Ningún dato de reservas del host se pierde en el despliegue (solo se borran nombres con más de 1 año).

## Assumptions

- La versión inicial de los documentos es la fecha de publicación (por ejemplo, 2026-10-14); cambiarla se hace en el código con una nueva publicación, no desde un panel.
- La aceptación es por usuario; hoy hay un usuario por cuenta.
- "Borrar el nombre" significa dejarlo vacío; la reserva conserva su referencia en el channel manager, que no es dato personal.
- Las copias de seguridad de la base (Neon) se borran solas en 7 días; no se borran manualmente al suprimir una cuenta, y así se informa.
- Los proveedores (OpenAI, Tavily, Resend, Firebase, Google) ya están declarados en /privacy; no reciben nombres de huéspedes.
- Un abogado revisará los textos antes de cobrar (Fase 1); esta versión es para la beta.
- El cifrado de campos de huéspedes y los datos de documentos llegan con #167 (TRA/SIRE).
