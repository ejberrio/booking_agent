# Feature 045: mensajes de huéspedes — leer y responder desde StayLever

**Issue:** #186 · **Rama:** `045-guest-messages` · **Depende de:** 044 (conexión Beds24), 025 (avisos), 028 (privacidad)

## Por qué
El anfitrión responde a sus huéspedes entrando a Airbnb, Booking y Beds24 por separado. Ver y
contestar todo en un solo lugar, con una respuesta sugerida por la IA que él edita, le ahorra
tiempo y mejora el tiempo de respuesta (que las plataformas premian).

## Lo que permite Beds24 (API V2, verificado el 11-nov-2026)
- **Leer:** `GET /bookings/messages`, filtrando por `bookingId`, `propertyId`, `filter=unread`, `maxAge` (≤ 999 días) y `source`.
  - Campos: `id`, `bookingId`, `message`, `source` (`guest`, `host`, `internalNote` o `system`), `read`, `time` y adjunto.
- **Enviar:** `POST /bookings/messages` `[{bookingId, message}]`.
  - Solo funciona en reservas de OTA: Beds24 lo entrega por la mensajería de Airbnb y de Booking.com.
- **Marcar leído:** `PATCH /bookings/messages?bookingId=…` `{read:true}`.
- **Permisos:** `read:bookings-personal` para leer y `write:bookings-personal` para enviar y marcar leído. El token de producción ya los tiene; el asistente (044) debe pedir el de escritura a los anfitriones nuevos.
- **Costo:** 100 créditos cada 5 minutos por cuenta, con costo dinámico por llamada. No hay webhook propio de mensajes: según Beds24, la actividad de mensajes viaja en el webhook de reservas.

## Historias
1. **(P1) Bandeja:** veo las conversaciones de mis reservas (en curso, próximas y recientes), con las no leídas primero y un contador en el menú.
2. **(P1) Responder:** abro una conversación, leo el hilo y respondo. El mensaje sale por el canal de la reserva.
3. **(P1) Sugerencia de la IA:** pulso «Sugerir respuesta» y la IA propone un texto en el idioma del huésped, que yo **edito**. Nada se envía de forma automática.
4. **(P2) Aviso:** cuando llega un mensaje nuevo de un huésped me llega un aviso al celular, sin el texto ni el nombre.

## Requisitos
- **FR-001 Sin copia local:**
  - los mensajes se leen **en vivo** desde Beds24 al abrir la bandeja o un hilo, y **no se guardan** en la base de StayLever;
  - no hay retención extra ni datos de huéspedes nuevos en la base;
  - en memoria se cachean 60 s por cuenta para no gastar créditos.
- **FR-002 Bandeja** (`GET /messages`):
  - reservas con mensajes de los últimos 90 días, agrupadas por reserva;
  - por cada una: unidad, canal, fechas, último mensaje (recortado a 140 caracteres), no leídos y nombre del huésped (el que ya se muestra en la app, 028).
- **FR-003 Hilo** (`GET /messages/{booking}`):
  - mensajes de huésped, anfitrión y sistema en orden; las notas internas se muestran como notas;
  - al abrirlo se marcan leídos en Beds24.
- **FR-004 Enviar** (`POST /messages/{booking}`):
  - texto de 1 a 2.000 caracteres; solo en reservas de OTA (Airbnb o Booking), con un mensaje claro si no se puede;
  - quién envía queda en la auditoría (sin el texto).
- **FR-005 Sugerir respuesta** (`POST /messages/{booking}/suggest`):
  - **antes** de enviar el hilo a la IA se quitan los datos personales (nombre, correo, teléfono, documentos, enlaces);
  - el contexto que va a la IA: últimos 10 mensajes, fechas, noches, canal, nombre de la unidad e idioma del hilo;
  - devuelve un borrador que el anfitrión edita, y nada se envía solo;
  - cuenta en el uso de IA de la cuenta (027) y no se guardan ni el prompt ni la respuesta.
- **FR-006 Aviso de mensaje nuevo:**
  - si el webhook de reservas (020) trae `messages[]` con un mensaje de huésped nuevo, se envía un aviso al celular **una vez por mensaje**;
  - el aviso no lleva texto ni nombre: «Tienes un mensaje nuevo de un huésped (Booking, 12–14 dic)».
- **FR-007 Modo sin conexión:** la bandeja explica que los mensajes requieren conectar Beds24 y enlaza al asistente.
- **FR-008 Privacidad:**
  - solo la cuenta dueña ve sus mensajes, nunca el administrador de plataforma, y nunca van a logs;
  - se actualizan la Política de privacidad (es/en/pt) y `docs/data-inventory.md`: los mensajes se procesan en tránsito, sin guardarse, y se envían anonimizados al proveedor de IA solo cuando el anfitrión pide una sugerencia.
- **FR-009 Asistente 044:** la lista de permisos del paso 1 pide **escritura en bookings-personal**.

## Criterios de éxito
- **SC-001** El anfitrión responde un mensaje de Booking o Airbnb desde StayLever y el huésped lo recibe en la plataforma.
- **SC-002** La sugerencia de la IA nunca contiene el nombre, el correo ni el teléfono del huésped tal como venían (prueba automática).
- **SC-003** Abrir la bandeja no consume más de 2 llamadas a Beds24, y el contador del menú como máximo 1 cada 5 minutos.

## Fuera de alcance
- Enviar o recibir adjuntos.
- Respuestas automáticas y plantillas programadas.
- Mensajes de reservas directas.
- Reseñas.
