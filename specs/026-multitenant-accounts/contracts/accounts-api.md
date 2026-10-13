# Contract: 026 — cuentas, acceso y administración

Convenciones: todas las rutas de la API salvo `/health`, `/auth/*` y `/hooks/*` exigen `Authorization: Bearer <token de sesión>` (lo añade el proxy de la web desde la cookie `sl_session`). Sin sesión válida → `401 {"detail": "Sesión no válida"}`. Un recurso de otra cuenta responde **404** igual que uno inexistente. Mensajes de error traducibles (es/en/pt) como hoy.

## API — acceso (`/auth/*`, solo llamado por las rutas de la web)

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `POST /auth/login` | `{email, password, kind: "web"\|"app", ip}` | `200 {token, expires_at, user}` · `401` genérico · `429 {"detail": "Demasiados intentos…", retry_after}` · `403` correo sin verificar (`{"detail":"Verifica tu correo","code":"email_unverified"}`) · `403` cuenta desactivada |
| `POST /auth/register` | `{name, email, password, invite_code?, language}` | `202 {"status":"check_email"}` siempre que los datos sean válidos (si el correo ya existe se envía "ya tienes cuenta" y no se consume la invitación) · `400` invitación inválida/vencida/usada/revocada o requerida · `503` correo no configurado |
| `POST /auth/verify-email` | `{token}` | `200 {token: <sesión>, …}` (entra al verificar) · `400` enlace vencido/usado |
| `POST /auth/resend-verification` | `{email}` | `202` siempre |
| `POST /auth/forgot-password` | `{email, language}` | `202` siempre |
| `POST /auth/reset-password` | `{token, password}` | `200` (revoca todas las sesiones del usuario) · `400` |
| `POST /auth/logout` | (Bearer) | `204` revoca la sesión actual |
| `POST /auth/logout-all` | (Bearer) | `204` revoca todas las sesiones del usuario |
| `GET /auth/me` | (Bearer) | `{user:{id,name,email,email_verified,language,is_platform_admin}, account:{id,name}}` |
| `GET /auth/claim-status` | — | `{"claimable": bool}` (true solo si la cuenta 1 no tiene miembros) |
| `POST /auth/claim` | `{name, email, password, kind}` | `200 {token,…}` crea el dueño de la cuenta 1 con `is_platform_admin` · `409` ya reclamada |
| `POST /auth/google/start` | `{mode:"login"\|"register", invite_code?, client:"web"\|"app", challenge?, next?}` | `{url}` (Google, con `state` y PKCE) · `503` Google no configurado |
| `POST /auth/google/callback` | `{code, state}` | web: `{token, expires_at}` · app: `{handoff_code}` · `400 {"code":"invite_required"}` / estado inválido |
| `POST /auth/handoff` | `{code, verifier}` | `{token, expires_at}` (sesión `app`, 90 días) · `400` |

## Web — rutas propias (fijan/borran la cookie)

`POST /api/auth/login|register|logout|logout-all|forgot|reset|verify|claim` (reenvían a la API; `claim` exige además la contraseña compartida actual `APP_PASSWORD`, comparada en tiempo constante, y solo si `claim-status` es true) · `GET /api/auth/google/start?mode&invite&client&challenge` → 302 a Google · `GET /api/auth/google/callback` → web: cookie + 302 `/`; app: 302 `com.staylever.app://auth?code=…` · `GET /api/auth/handoff?code&verifier` → cookie de 90 días + 302 `/`.

Páginas públicas: `/login`, `/register?code=…`, `/forgot`, `/reset?token=…`, `/verify?token=…`, `/claim`. El proxy `/api/proxy/*` responde `404` a `auth/*` y nunca reenvía `Authorization`, `Cookie` ni cabeceras de identidad que envíe el navegador.

## API — datos de la cuenta (nuevas o con cambio de alcance)

| Ruta | Notas |
|---|---|
| `GET /units` | `[{id, name, property_id, property_name, city, currency}]` de la cuenta (la web elige la unidad activa de aquí; lista vacía → estado vacío) |
| `GET /account` · `PATCH /account {name}` | datos de la cuenta |
| `GET/PUT/DELETE /settings/secrets/*` | **solo secretos de la cuenta** (`beds24_refresh_token`, `beds24_webhook_key`); canje del código de invitación de Beds24 → importa propiedades **a esta cuenta**; `409` si la propiedad ya pertenece a otra cuenta |
| `GET /status` | conexión del channel manager **de la cuenta** (`connected: false` → estado vacío) |
| `POST /hooks/beds24` | la clave `x-staylever-key` identifica la cuenta; clave desconocida → `401`; `propertyId` de otra cuenta → ignorado |
| resto (`/pricing/*`, `/suggestions/*`, `/bookings`, `/chat/*`, `/push/*`, `/pois`, `/scan-config`, `/preferences`, `/calendar-notes/*`, `/sync/*`) | mismo contrato que hoy, filtrado por la cuenta de la sesión |

## API — administrador de plataforma (`/admin/*`, `is_platform_admin`; si no → 403)

| Ruta | Respuesta |
|---|---|
| `GET /admin/invites` | `[{id, last4, note, status, expires_at, used_by_account?:{id,name}, created_at}]` |
| `POST /admin/invites {note?, days?=30}` | `{id, code, …}` (**el código completo solo aquí**) |
| `DELETE /admin/invites/{id}` | revoca si no se usó · `409` si ya se usó |
| `GET /admin/accounts` | `[{id, name, owner_email, status, created_at, last_seen_at, connected, properties}]` — sin precios, reservas ni conversaciones |
| `POST /admin/accounts/{id}/disable` · `/enable` | desactiva (revoca sesiones) / reactiva · la cuenta del propio administrador no se puede desactivar |
| `GET /admin/settings` · `PATCH /admin/settings {registration_open}` | interruptor del registro |
| `GET/PUT/DELETE /admin/secrets/*` | secretos de plataforma (IA, búsqueda, Firebase, correo, Google) — mismo formato que `/settings/secrets` |
| `GET/PUT /admin/llm-config` | configuración del modelo (antes global) |

## App Android 1.1.0

- `AndroidManifest`: intent-filter `VIEW` para `com.staylever.app://auth`.
- Dependencia `@capacitor/browser`. El botón "Entrar con Google" en la app abre `https://staylever.com/api/auth/google/start?client=app&challenge=<S256(verifier)>` en el navegador del sistema; al recibir `appUrlOpen` con `code`, cierra el navegador y navega a `/api/auth/handoff?code=…&verifier=…`.
- User-Agent `StayLeverApp/1.1.0`; con versión < 1.1.0 la web oculta el botón de Google y muestra "actualiza la app para entrar con Google".
