# Cuentas y acceso (feature 026)

StayLever tiene **cuentas aisladas** (cada anfitrión ve solo lo suyo) y **acceso por usuario**
(correo y contraseña, o Google). Diseño: [ADR 0007](adr/0007-multitenancy.md).

## Para el host

- **Entrar:** staylever.com/login con tu correo y tu contraseña. En la app de Android, igual;
  la sesión dura 90 días (7 en el navegador).
- **Olvidé mi contraseña:** en la pantalla de entrada. Llega un enlace de `no-reply@mail.staylever.com`
  que vence en 1 hora y sirve una vez. Al cambiarla se cierran tus otras sesiones.
- **Ajustes → Mi cuenta:** verificar el correo, cambiar tu nombre y el de la cuenta (el que se ve
  en el menú lateral), cambiar la contraseña y
  "Cerrar todas mis sesiones" (por ejemplo, si pierdes el teléfono).

## Primera vez (reclamar la cuenta nº 1)

Al desplegar la entrega 2, tus datos están en la cuenta nº 1 sin usuario. Al abrir la web aparece
**"Configura tu acceso"**: escribe la contraseña de siempre (`APP_PASSWORD` de la web), tu nombre,
tu correo y una contraseña nueva. Quedas como dueño y **administrador de la plataforma**. Después,
la contraseña de siempre ya no sirve para entrar.

## Invitar anfitriones (beta)

- **Administración → Invitaciones:** escribe para quién es (p. ej. "Ana, Cartagena") y pulsa
  "Crear código". El código `SL-XXXX-XXXX` se muestra **una sola vez**: copia el código o el
  enlace de registro (`staylever.com/register?code=…`) y compártelo. Vence en 30 días (ajustable)
  y sirve una vez; puedes revocarlo mientras no se use.
- El anfitrión crea su cuenta (nombre, correo, contraseña dos veces), confirma su correo y entra a
  una StayLever vacía que le indica conectar su Beds24 en Ajustes.
- **Administración → Cuentas:** ves cada cuenta (dueño, uso, si tiene channel manager, nº de
  propiedades), sin sus precios, reservas ni conversaciones. "Desactivar" cierra sus sesiones y
  el escaneo la omite; sus datos se conservan y "Reactivar" lo deshace.
- **Registro abierto:** apagado (beta) = solo con código; encendido = cualquiera con un correo.

## Correo (Resend)

- **Recibir:** Cloudflare Email Routing reenvía `hello@`, `privacy@` y `support@staylever.com`
  (y `hola@`) a la bandeja del host; cualquier otra dirección se descarta. Contacto público en
  `/welcome` → `hello@`; en `/privacy` → `privacy@`. Los registros MX/SPF de `staylever.com` son de
  Cloudflare y no chocan con Resend, que envía desde el subdominio `mail.staylever.com`.

- Dominio de envío `mail.staylever.com` (registros DKIM/SPF en Cloudflare, región sa-east-1).
- La clave (`re_…`, permiso *Sending access*) se pega en **Ajustes → Secretos → "Correo (Resend
  API key)"** — es un secreto de plataforma: solo lo ve el administrador. Sin clave, no salen
  correos (verificación y recuperación) y el resto de la app funciona igual.
- `PUBLIC_BASE_URL` (api) define la dirección de los enlaces: producción `https://staylever.com`
  (por defecto); pruebas, el dominio de staging.

## Entrar con Google

- **Para los anfitriones:** botón **"Entrar con Google"** en la entrada y **"Crear cuenta con Google"**
  en el registro (con el código de invitación mientras el registro esté cerrado). Si su correo de
  Google ya tiene cuenta en StayLever, se vincula solo (Google confirma el correo). En la app de
  Android requiere la **versión 1.1.0**: Google se abre en el navegador del teléfono y vuelve a la app.
- **Para el administrador (una sola vez):** Google Cloud, proyecto `staylever` → Google Auth
  Platform: pantalla de consentimiento "StayLever" (usuarios externos, solo `openid email profile`,
  sin verificación de Google) y cliente web **"StayLever web"** con los URI de retorno
  `https://staylever.com/api/auth/google/callback` y el de staging. El **ID** y el **secreto** se
  pegan en **Ajustes → Secretos** ("Google OAuth client ID/secret", secretos de plataforma) en cada
  ambiente. Sin ellos el botón no aparece. Si el secreto se pierde, se genera otro en el mismo cliente.
- **Publicación:** mientras la pantalla de Google esté "En prueba", solo entran los usuarios de
  prueba que agregues en Público; al **publicarla** ("En producción") entra cualquiera.

## Privacidad (feature 028)

- **Términos y Privacidad**: casilla obligatoria al registrarse (correo y Google) y al reclamar.
  Quien no ha aceptado la versión vigente ve una pantalla de aceptación y la API responde
  `403 terms_required` hasta que acepte. Publicar una versión nueva = cambiar `LEGAL_VERSION`
  (`apps/api/app/core/legal.py`) y los textos de `/terms` y `/privacy`.
- **Nombre del huésped**: lo ve solo la cuenta dueña; se borra 1 año después de la salida (el
  cron diario `scan_daily` lo limpia en todas las cuentas).
- **Ajustes → Tus datos**: descargar copia (JSON) y borrar la cuenta (nombre + contraseña, o
  código por correo si entra solo con Google). En Administración aparece como "Eliminada".
- Inventario completo: [data-inventory.md](data-inventory.md).

## Uso y límites de IA (feature 027)

- Cada cuenta tiene **300 mensajes al asistente por mes** y **5 búsquedas web por día** en el
  escaneo diario (valores de la plataforma: `AI_CHAT_LIMIT_MONTH`, `AI_SEARCH_LIMIT_DAY`).
- Al 80 % el anfitrión ve un aviso; al 100 % el asistente responde que llegó al límite y cuándo
  se renueva (día 1 del mes, hora de Colombia) sin llamar a la IA. Si hay un cambio pendiente de
  confirmar, su confirmación siempre se atiende. Las sugerencias diarias no cuentan.
- **Administración → Uso de IA**: por mes y cuenta, mensajes, llamadas, tokens, búsquedas y costo
  estimado; los límites de cada cuenta se cambian ahí ("Por defecto" vuelve a los de la plataforma).
- Costos estimados con `AI_PRICES` (JSON, USD por millón de tokens `[entrada, salida]` por modelo y
  `"search"` por búsqueda). Un modelo sin precio se cuenta como "sin precio".

## Modo sin conexión (feature 029)

- Una cuenta nueva puede **usar StayLever sin channel manager**: "Usar sin conexión" → crea el
  apartamento (nombre, ciudad, moneda, precio entre semana y de viernes/sábado, enlaces del anuncio
  y del iCal de exportación de Airbnb/Booking). StayLever siembra 365 noches de precio.
- La ocupación llega del **iCal** (escaneo diario o "Sincronizar calendarios ahora" en Ajustes) y
  se puede marcar a mano en el calendario. Las reservas del iCal no traen nombre de huésped.
- Sugerencias, precios en bloque y el asistente funcionan igual, pero **no publican**: StayLever
  guarda el precio y la app muestra enlaces para copiarlo en Airbnb (multicalendario) y Booking
  (extranet). `account.channel_mode = manual`; adaptador `ManualChannelAdapter`.
- iCal: solo https de Airbnb, Booking, Vrbo o Google Calendar; el enlace completo es privado
  (da acceso al calendario) y no se muestra ni se registra.

## Interruptor de transición (`AUTH_MODE`, servicio api)

- `legacy` (por defecto): con sesión, la cuenta de la sesión; sin sesión, la cuenta nº 1. Permite
  desplegar web y API por separado sin cortar el servicio.
- `sessions`: toda petición exige sesión. Se activa cuando el host ya entró con su usuario en la
  web y en la app.

## Seguridad

- Contraseñas con Argon2id; sesiones y enlaces guardados solo como hash; mensajes de error
  genéricos (no revelan si un correo existe); 10 fallos por correo o 50 por IP en 15 minutos
  bloquean temporalmente.
- La web guarda la sesión en una cookie httpOnly y el proxy la envía a la API; el navegador no
  puede llamar a las rutas de acceso de la API ni imponer cabeceras de identidad.
