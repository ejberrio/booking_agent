# Feature Specification: Aplicación móvil (Android primero, iPhone después)

**Feature Branch**: `025-mobile-app`
**Created**: 2026-10-09
**Status**: Draft
**Input**: User description: "Aplicación móvil (Android y iPhone): primero un APK, luego evaluar tiendas (issue #140)."

## Contexto

StayLever es hoy una web (staylever.com). El host quiere usarla como **app en el celular**, con **avisos** (notificaciones) de lo importante. Decisiones del host (2026-10-09):

1. **Contenedor nativo (Capacitor)** sobre la web actual: una sola interfaz que mantener.
2. **Android primero** (gratis, APK instalable sin Play Store). **iPhone cuando el host tenga la cuenta de Apple**: el diseño lo deja preparado, pero no se construye ahora.
3. **Notificaciones**: reservas nuevas, modificadas y canceladas, y **sugerencias nuevas** del escaneo diario.
4. La **sesión** en la app dura **90 días** (la web sigue en 7).

Restricción: el repositorio es **público** → ninguna llave de firma ni credencial puede quedar en el código; el host las carga como secretos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instalar StayLever en el Android sin Play Store (Priority: P1)

Como host quiero descargar un APK, instalarlo en mi Android y usar StayLever como una app (icono propio, pantalla completa, sin barra del navegador), con todo lo que hace la web.

**Why this priority**: es el objetivo de la primera etapa.

**Independent Test**: descargar el APK de la última versión publicada, instalarlo, abrir "StayLever", iniciar sesión, usar Panorama, Calendario, Sugerencias, Ofertas, Ajustes y el chat flotante; cerrar y volver a abrir sin que pida la contraseña.

**Acceptance Scenarios**:

1. **Given** una versión publicada, **When** el host la descarga en el celular, **Then** encuentra un APK con instrucciones de instalación (permitir apps de origen desconocido).
2. **Given** la app instalada, **When** la abre, **Then** ve el icono y el nombre StayLever, una pantalla de carga y luego la pantalla de acceso o el Panorama, sin barra de navegador.
3. **Given** sesión iniciada en la app, **When** vuelve días después (hasta 90), **Then** sigue dentro; cerrar sesión o cambiar la contraseña la invalida.
4. **Given** un enlace externo (Beds24, Booking.com, Airbnb), **When** lo toca, **Then** se abre en el navegador del teléfono, no dentro de la app.
5. **Given** el botón "atrás" de Android, **When** lo pulsa, **Then** vuelve a la pantalla anterior; en el Panorama sale de la app.
6. **Given** una nueva versión firmada con la misma llave, **When** la instala encima, **Then** se actualiza sin perder la sesión.
7. **Given** sin conexión, **When** abre la app, **Then** ve un mensaje claro de "sin conexión" con opción de reintentar.

---

### User Story 2 - Avisos de reservas (Priority: P1)

Como host quiero recibir un aviso en el celular cuando entra, cambia o se cancela una reserva, con fechas y canal.

**Why this priority**: es el valor principal de tener la app en el bolsillo.

**Independent Test**: con la app instalada y los avisos permitidos, una reserva nueva informada por Beds24 genera un aviso "Nueva reserva · Booking.com · 14–16 nov"; tocarlo abre el Calendario en ese mes.

**Acceptance Scenarios**:

1. **Given** la app instalada, **When** se abre por primera vez tras iniciar sesión, **Then** pide permiso para avisos y registra el teléfono.
2. **Given** una reserva nueva/modificada/cancelada detectada (aviso de Beds24 o sincronización), **When** se guarda, **Then** cada teléfono con avisos de reservas activos recibe un aviso con tipo, canal y fechas (sin datos personales del huésped).
3. **Given** la misma reserva detectada dos veces (aviso + sincronización diaria), **When** no cambió, **Then** no se repite el aviso.
4. **Given** el host toca el aviso, **When** se abre la app, **Then** va al Calendario del mes de la reserva.

---

### User Story 3 - Aviso de sugerencias nuevas (Priority: P2)

Como host quiero un aviso cuando el escaneo diario crea sugerencias de precio nuevas.

**Independent Test**: un escaneo con 3 sugerencias nuevas envía "3 sugerencias de precio nuevas"; tocarlo abre Sugerencias. Un escaneo sin nuevas no envía nada.

**Acceptance Scenarios**:

1. **Given** el escaneo crea N > 0 sugerencias nuevas, **When** termina, **Then** se envía un aviso con N.
2. **Given** N = 0, **When** termina, **Then** no hay aviso.

---

### User Story 4 - Controlar los avisos desde Ajustes (Priority: P2)

Como host quiero ver los teléfonos registrados, activar o desactivar cada tipo de aviso y enviar un aviso de prueba.

**Acceptance Scenarios**:

1. **Given** Ajustes → Notificaciones, **When** el host la abre, **Then** ve los teléfonos registrados (modelo/plataforma, último uso) y los interruptores "Reservas" y "Sugerencias".
2. **Given** "Enviar aviso de prueba", **When** lo pulsa, **Then** llega un aviso a sus teléfonos y la app confirma el resultado.
3. **Given** las credenciales del servicio de avisos sin configurar, **When** abre la tarjeta, **Then** ve cómo configurarlas (guía como la de los demás secretos).
4. **Given** un teléfono que ya no existe (token inválido), **When** falla un envío, **Then** se desactiva solo.

---

### User Story 5 - Preparado para publicar e iPhone (Priority: P3)

Como host quiero un documento con los pasos y requisitos para Google Play y para iPhone (cuenta de Apple, TestFlight, App Store), para decidir cuándo dar ese paso.

**Acceptance Scenarios**:

1. **Given** el documento, **When** el host lo lee, **Then** sabe costos, cuentas, requisitos de revisión (política de privacidad, cuenta de prueba, "funcionalidad mínima" de Apple), y los pasos técnicos pendientes para iPhone.

### Edge Cases

- Avisos denegados en el teléfono → la app sigue funcionando; Ajustes indica que ese teléfono no recibe avisos.
- Varios teléfonos → todos reciben (según sus preferencias).
- Sesión vencida → la app muestra la pantalla de acceso, como la web.
- Credenciales de avisos ausentes o inválidas → no se envían avisos, sin romper reservas ni escaneo; queda registrado.
- Webhook y sincronización detectan la misma reserva → un solo aviso por cambio real.
- El APK nunca contiene contraseñas, tokens de Beds24 ni llaves privadas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST producir un APK de Android firmado, con nombre e icono StayLever, que abra staylever.com a pantalla completa con todas las funciones de la web.
- **FR-002**: La construcción del APK MUST ser automática y reproducible; la llave de firma y la configuración del servicio de avisos MUST venir de secretos fuera del repositorio.
- **FR-003**: Cada versión MUST publicarse con su APK descargable desde el teléfono e instrucciones de instalación.
- **FR-004**: La sesión iniciada desde la app MUST durar 90 días; la de la web sigue en 7 días. Cerrar sesión o cambiar la contraseña invalida ambas.
- **FR-005**: Los enlaces a otros dominios MUST abrirse en el navegador del sistema; el botón atrás MUST navegar hacia atrás y salir desde el Panorama.
- **FR-006**: Sin conexión, la app MUST mostrar un aviso claro con reintento.
- **FR-007**: La app MUST pedir permiso de avisos y registrar el teléfono en el servidor (identificador del dispositivo, plataforma, modelo, versión de la app), actualizándolo si cambia.
- **FR-008**: El servidor MUST enviar avisos de reservas nuevas, modificadas y canceladas (tipo, canal, fechas; sin datos personales del huésped) a los teléfonos con ese tipo activo, sin duplicar el mismo cambio.
- **FR-009**: El servidor MUST enviar un aviso cuando el escaneo diario cree N > 0 sugerencias nuevas.
- **FR-010**: Tocar un aviso MUST abrir la pantalla relacionada (Calendario del mes / Sugerencias).
- **FR-011**: Ajustes MUST listar teléfonos registrados, permitir activar/desactivar avisos de reservas y sugerencias, quitar un teléfono y enviar un aviso de prueba.
- **FR-012**: Teléfonos con identificador inválido MUST desactivarse automáticamente.
- **FR-013**: Las credenciales del servicio de avisos MUST guardarse como secreto de la app (cifrado, con guía en Ajustes); la falta de credenciales no MUST afectar reservas ni escaneo.
- **FR-014**: MUST existir un documento con requisitos y pasos para Google Play y para iPhone (cuenta Apple, TestFlight, App Store) y la checklist técnica pendiente para iOS.
- **FR-015**: Textos nuevos en es/en/pt; los avisos se envían en el idioma preferido del host.

### Key Entities

- **Teléfono registrado**: identificador para avisos, plataforma, modelo, versión de la app, preferencias (reservas, sugerencias), activo, último uso.
- **Registro de avisos enviados**: tipo, referencia (reserva/escaneo), huella del cambio, fecha; evita duplicados.

## Success Criteria *(mandatory)*

- **SC-001**: El host instala el APK en su Android y usa todas las secciones sin barra de navegador.
- **SC-002**: Una reserva nueva informada por Beds24 llega como aviso en menos de 2 minutos.
- **SC-003**: 0 avisos duplicados por el mismo cambio de reserva.
- **SC-004**: El host no vuelve a escribir la contraseña en la app durante 90 días (salvo cerrar sesión o cambiarla).
- **SC-005**: Ningún secreto (llave de firma, credenciales) aparece en el repositorio ni en el APK.

## Assumptions

- La infraestructura actual (Railway + Cloudflare) lo soporta sin cambios de plan: la app usa la misma web y API; el servicio de avisos (Firebase Cloud Messaging) es gratuito.
- El host crea un proyecto gratuito de Firebase y carga sus credenciales; también crea la llave de firma con el script provisto.
- iPhone: fuera de esta entrega (requiere cuenta de Apple y Xcode completo); el diseño lo contempla.
- Fuera de alcance: publicar en tiendas, multitenant, plan de negocio, modo sin conexión con datos.
