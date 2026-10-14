# Inventario de datos (feature 028, Ley 1581 de 2012)

Documento interno. StayLever es **Responsable** de los datos de los anfitriones (sus usuarios)
y **Encargado** de los datos de los huéspedes de cada anfitrión. Revisar con un abogado antes
de cobrar (Fase 1). Versión de los documentos públicos: `LEGAL_VERSION` en
`apps/api/app/core/legal.py` (hoy `2026-10-14`).

| Dato | Titular | Dónde | Para qué | Quién lo ve | Cuánto tiempo |
|---|---|---|---|---|---|
| Nombre, correo, idioma del usuario | Anfitrión | Neon (EE. UU.) `app_user` | Acceso y avisos por correo | El usuario; el administrador ve el correo del dueño en el panel | Mientras exista la cuenta |
| Contraseña | Anfitrión | `app_user.password_hash` (Argon2id, irreversible) | Acceso | Nadie | Mientras exista la cuenta |
| Identificador de Google | Anfitrión | `app_user.google_sub` | Entrar con Google | Nadie (técnico) | Mientras exista la cuenta |
| Sesiones, enlaces y códigos | Anfitrión | `user_session`, `auth_token` (solo hash) | Seguridad | Nadie | Hasta vencer; se borran con la cuenta |
| Aceptación de Términos y Privacidad | Anfitrión | `terms_acceptance` (versión, fecha) | Prueba del consentimiento | El usuario (en su copia) | Mientras exista la cuenta |
| Intentos de acceso | — | `auth_attempt` (hash del correo, IP) | Límite de fuerza bruta | Nadie | Ventana de 15 min (filas antiguas sin uso) |
| Nombre del huésped | Huésped (Responsable: anfitrión) | `booking.guest_name` | Mostrar quién reserva | Solo la cuenta dueña; nunca el administrador, logs, avisos ni la IA | **1 año tras la salida** (limpieza diaria del cron) |
| Propiedades, calendario, tarifas, reservas (sin datos personales), sugerencias, promociones, notas | Anfitrión | Tablas `AccountOwned` | Sugerir y publicar precios | Solo la cuenta | Mientras exista la cuenta |
| Conversaciones con el asistente | Anfitrión | `conversation`, `message`, `agent_action` | Asistente | Solo la cuenta | Mientras exista la cuenta |
| Credenciales del channel manager | Anfitrión | `secret_entry` (cifradas, Fernet) | Conectar Beds24 | Nadie (solo el servicio) | Mientras exista la cuenta |
| Teléfonos para avisos | Anfitrión | `push_device` (token de Firebase, modelo) | Avisos al celular | Solo la cuenta | Hasta desactivarse o borrar la cuenta |
| Eventos públicos de la ciudad | — | `event` (compartido) | Sugerencias | Todas las cuentas de esa ciudad | Indefinido (datos públicos) |
| Registros técnicos | — | Railway (EE. UU.) | Operar y depurar | Administrador | Retención de Railway; sin correos completos, tokens ni nombres de huéspedes |
| Copias de seguridad de la base | Todos | Neon (ramas `antes-de-…`) | Recuperación ante fallos | Administrador | Se borran solas en máximo 7 días |

## Proveedores (encargados de StayLever)

| Proveedor | País | Qué recibe |
|---|---|---|
| Railway | EE. UU. | Aloja la web y la API (todo el tráfico) |
| Neon | EE. UU. (us-east-1) | Base de datos |
| OpenAI | EE. UU. | Calendario, precios y mensajes del asistente; **nunca nombres de huéspedes** |
| Tavily | EE. UU. | Búsquedas de eventos públicos por ciudad |
| Resend | Brasil (sa-east-1) / EE. UU. | Correo y nombre del usuario para correos de acceso |
| Google Firebase | EE. UU. | Token del teléfono y texto del aviso (sin nombres de huéspedes) |
| Google (Entrar con Google) | EE. UU. | Inicio de sesión del usuario que lo elige |
| Beds24 | Alemania / UE | Es el channel manager del anfitrión: origen de reservas y destino de precios |
| Cloudflare | EE. UU. | DNS y reenvío de hello@/privacy@/support@ a la bandeja del administrador |

## Derechos del titular

- **Acceso**: Ajustes → Tus datos → Descargar copia (`GET /account/export`): todo lo de la cuenta, sin credenciales.
- **Rectificación**: Ajustes → Mi cuenta (nombre, nombre de la cuenta, contraseña).
- **Supresión**: Ajustes → Tus datos → Borrar mi cuenta (`POST /account/delete`): borra todas las filas de la cuenta, el usuario y sus sesiones; la cuenta queda como lápida `deleted` sin nombre. La cuenta nº 1 no se borra así.
- **Consultas y reclamos**: privacy@staylever.com, respuesta en máximo 15 días hábiles.
