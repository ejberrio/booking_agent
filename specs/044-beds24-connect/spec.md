# Feature 044: conectar Beds24 desde StayLever (asistente con código de invitación)

**Issue:** #150 · **Épica:** #157 (Fase 1, precios automáticos con Beds24) · **Rama:** `044-beds24-connect`
**Depende de:** 017 (secretos), 026 (cuentas), 029 (modo sin conexión), 042 (valor de las reservas)

## Por qué
Hoy un anfitrión nuevo solo puede conectar Beds24 si encuentra, dentro de Ajustes → Secretos, un
campo para pegar el código de invitación. Después del canje:
- no se prueba la conexión ni se importa nada;
- se importan **todas** las propiedades, y si una ya está en otra cuenta falla todo;
- si el token deja de servir, nadie se entera;
- quien empezó «sin conexión» (029) no tiene cómo pasar a conectado sin perder lo que llevaba.

Es el principal freno para sumar anfitriones beta (#149) y para la Fase 1.

## Estado actual (lo que ya existe y se reutiliza)
- Canje `POST /settings/secrets/beds24_refresh_token/invite` (`exchange_invite_code`) y token por cuenta cifrado con Fernet, write-only, con auditoría.
- El access token se renueva solo. El refresh token vive mientras la corrida diaria lo use (30 días).
- `PropertyOwnedElsewhere` evita conectar una propiedad que ya está en otra cuenta.
- La página «Conexión» (`/onboarding`) tiene probar, importar y un campo numérico de «propiedad activa». Su texto menciona el «.env», y eso ya no aplica.

## Historias de usuario
1. **(P1) Conectar por primera vez:**
   - como anfitrión con Beds24, sigo un asistente de 4 pasos y en menos de 5 minutos veo mi calendario y mis precios en StayLever;
   - no tengo que saber qué es un token.
2. **(P1) Elegir qué conectar:** si mi cuenta de Beds24 tiene varias propiedades (o una que no es mía), elijo cuáles traer. Las demás se ignoran.
3. **(P1) Enterarme si se cae la conexión:**
   - si Beds24 revoca el token o deja de responder por permisos, me llega un aviso al celular y un correo;
   - la app muestra un aviso con «Reconectar».
4. **(P2) Pasar de «sin conexión» a conectado:** si empecé sin conexión, al conectar Beds24 asocio cada apartamento manual con su habitación de Beds24 y conservo mi historial.
5. **(P2) Guía para las plataformas:** si aún no tengo Airbnb y Booking conectados a Beds24, hay una guía paso a paso en es/en/pt con los bloqueos conocidos.

## Requisitos
- **FR-001 Asistente «Conectar Beds24»:** reemplaza la página «Conexión»; también se llega desde la pantalla de cuenta vacía y desde el aviso de conexión caída.
  1. **Generar el código:**
     - botón que abre Beds24 en la página de la API (Settings → Marketplace → API);
     - lista de permisos exactos a marcar: lectura de bookings, bookings-personal, inventory, properties y channels; escritura solo de inventory y channels;
     - botón «copiar» para cada uno y aviso de que el código vence en minutos.
  2. **Pegar y validar:**
     - se canjea el código y se prueba la conexión al momento (propiedades y reservas);
     - si Beds24 expone los permisos del token, se verifican y se dice cuál falta;
     - mensajes claros: código vencido o usado, falta un permiso, Beds24 no responde.
  3. **Elegir propiedades y habitaciones:**
     - lista de lo que trae la cuenta de Beds24, con casillas (todo marcado por defecto);
     - lo que ya está conectado a otra cuenta de StayLever aparece deshabilitado, con el motivo, **sin abortar** el resto.
  4. **Importar:**
     - reservas del último año (con su valor, 042), precios y calendario, con indicador de progreso;
     - al terminar lleva al tablero.
- **FR-002 Selección persistente:**
  - la cuenta guarda qué propiedades y habitaciones de Beds24 sincroniza;
  - la corrida diaria, los avisos de reservas (020) y la importación solo tocan las elegidas;
  - se puede cambiar después en Conexión;
  - un conflicto con otra cuenta excluye esa propiedad y no detiene las demás.
- **FR-003 Salud de la conexión:**
  - estado persistente por cuenta: conectado, sin permisos o token inválido, con la fecha desde cuándo;
  - lo actualizan la corrida diaria, los avisos y cualquier llamada que falle por autenticación;
  - al pasar a inválido: aviso al celular (025) y correo (Resend) **una vez**, y un recordatorio a los 3 días si sigue igual;
  - además, un banner en la app con «Reconectar» (paso 1 del asistente);
  - al volver a conectar, se avisa que se restableció.
  - **Privacidad:** sin datos de huéspedes en avisos ni correos.
- **FR-004 De «sin conexión» a conectado:** si la cuenta está en modo manual, el paso 3 propone asociar cada apartamento manual con una habitación de Beds24, o crearlo nuevo. Al asociar:
  - se conservan la unidad y todo su historial: precios aplicados, sugerencias, notas, rentabilidad y finanzas;
  - las reservas que llegaron por iCal se concilian con las de Beds24 por fechas y canal; manda Beds24 y se quitan los duplicados;
  - los enlaces iCal quedan desactivados (se guardan por si se vuelve atrás);
  - desde ese momento los precios se leen y escriben en Beds24;
  - la cuenta pasa a `connected`.

  También se corrige que hoy un canje en modo manual guarde un token que nunca se usa.
- **FR-005 Guía de canales** (es/en/pt), enlazada desde el asistente:
  - cómo conectar Airbnb y Booking.com a Beds24;
  - bloqueos conocidos: co-anfitrión de Airbnb, Extranet Light de Booking, un solo channel manager por anuncio y Smart Pricing apagado;
  - qué revisar después (precios, disponibilidad).

  Al inicio es texto con enlaces a la ayuda oficial de Beds24; las capturas vienen después.
- **FR-006 Ajustes:** el campo para pegar un token a mano pasa a «Avanzado». El canje de código queda como atajo a «Reconectar».
- **FR-007 Seguridad:**
  - solo el dueño de la cuenta conecta o cambia la selección;
  - el token nunca sale en logs, respuestas ni errores;
  - en sandbox se mantiene el 409;
  - el aislamiento por cuenta es el de 026 (principio VI).

## Criterios de éxito
- **SC-001** Un anfitrión con Beds24 llega del registro a ver su calendario en menos de 5 minutos, sin ayuda.
- **SC-002** Una propiedad conectada a otra cuenta no impide importar las demás.
- **SC-003** Cuando el token deja de servir, el anfitrión recibe aviso en menos de 24 h (la siguiente corrida diaria o el primer error).
- **SC-004** Al pasar de «sin conexión» a conectado no se pierde ninguna sugerencia, nota ni registro de precios, y no quedan reservas duplicadas.

## Decisiones por confirmar con el anfitrión
1. **Selección por defecto:** todo marcado (recomendado) o nada marcado.
2. **Avisos de conexión caída:** celular + correo + banner, con un recordatorio a los 3 días (recomendado), o solo banner.
3. **Modo manual → conectado:** asociar cada apartamento manual a una habitación de Beds24 (recomendado), o empezar de cero e importar todo nuevo.

## Fuera de alcance
- Crear la cuenta de Beds24 por el anfitrión.
- Marketplace y revendedor de Beds24 (#151).
- Channex (#154).
- Capturas en la guía (fase 2).
