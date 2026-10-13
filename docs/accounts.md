# Cuentas y acceso (feature 026)

StayLever tiene **cuentas aisladas** (cada anfitrión ve solo lo suyo) y **acceso por usuario**
(correo y contraseña; Google llega en la entrega 4). Diseño: [ADR 0007](adr/0007-multitenancy.md).

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

- Dominio de envío `mail.staylever.com` (registros DKIM/SPF en Cloudflare, región sa-east-1).
- La clave (`re_…`, permiso *Sending access*) se pega en **Ajustes → Secretos → "Correo (Resend
  API key)"** — es un secreto de plataforma: solo lo ve el administrador. Sin clave, no salen
  correos (verificación y recuperación) y el resto de la app funciona igual.
- `PUBLIC_BASE_URL` (api) define la dirección de los enlaces: producción `https://staylever.com`
  (por defecto); pruebas, el dominio de staging.

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
