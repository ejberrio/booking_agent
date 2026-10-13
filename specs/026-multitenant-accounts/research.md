# Research: Multicliente mínimo (Feature 026)

Contexto técnico relevado el 2026-10-10 (mapa de supuestos single-tenant del código): la web valida una contraseña única (`APP_PASSWORD`) y firma una cookie sin identidad; el proxy `/api/proxy/*` reenvía todo a la API sin identidad; **la API no autentica** (confía en la red privada de Railway); 33 tablas, casi todas sin dueño; singletons (`AppPreference id=1`, `ScanConfig`, `ChannelManagerConnection`, `LLMConfig`) leídos con `.first()`; secretos en `secret_entry` (Fernet) con caché global por nombre; adaptador Beds24 construido por petición desde `settings` + secreto global; cron `scan_daily` toma la primera unidad; "Medellín"/COP fijos en prompts; 50 archivos de test con SQLite en memoria y `create_all`.

## D1. Aislamiento: una base compartida con `account_id` en todas las tablas del anfitrión + filtro automático del ORM

- **Decision**: añadir `account_id` (FK `account.id`, NOT NULL, indexado) a **todas** las tablas con datos del anfitrión (incluidas las hijas de `unit_type`), mediante un mixin `AccountOwned`. La sesión de base de datos de cada petición lleva la cuenta en `session.info`, y dos eventos de SQLAlchemy 2.0 hacen el resto:
  - `do_orm_execute` añade `with_loader_criteria(AccountOwned, account_id == X, include_aliases=True)` a todo SELECT/UPDATE/DELETE del ORM (incluye `session.get`, relaciones y `select_from`).
  - `before_flush` rellena `account_id` en objetos nuevos sin él y **rechaza** objetos con `account_id` distinto al de la sesión.
  - **Falla cerrado**: si una sentencia toca una entidad `AccountOwned` y la sesión no tiene cuenta ni permiso explícito de plataforma (`session.info["platform"]=True`, solo para el panel de administrador y el recorrido del cron), lanza `TenantContextMissing`.
- **Rationale**: el principio VI exige que ninguna ruta, tarea ni herramienta del agente vea datos ajenos. Con ~70 rutas, 20 servicios y 20 herramientas del agente, filtrar a mano cada consulta es propenso a olvidos; el filtro automático lo garantiza por defecto y las pruebas de "falla cerrado" detectan cualquier camino sin contexto. Poner `account_id` también en tablas hijas (calendario, tarifas, logs) evita joins para filtrar y hace el filtro uniforme. El código no usa `insert()`/`update()` de Core ni SQL crudo salvo `SELECT 1` (verificado), así que el ORM cubre todo.
- **Alternatives**: (a) Row Level Security de Postgres — robusto, pero las pruebas corren en SQLite y añade gestión de roles/`SET` por conexión; queda como refuerzo futuro. (b) Esquema o base por cliente — viola el principio V (infraestructura por cliente). (c) Filtrar a mano en cada servicio — demasiados puntos de olvido.

## D2. Identidad y sesiones viven en la API (base de datos), la web solo guarda una cookie opaca

- **Decision**: la API gestiona usuarios, contraseñas y sesiones. El token de sesión es aleatorio (32 bytes, `secrets.token_urlsafe`), se guarda **solo su SHA-256** en `user_session` (tipo web/app, vence 7/90 días, `last_used_at`, `revoked_at`). La web lo guarda en la cookie httpOnly `sl_session` (nombre nuevo: las cookies antiguas dejan de valer solas). El proxy elimina cualquier `Authorization`/`X-*` de identidad que mande el navegador y añade `Authorization: Bearer <token>` desde la cookie. La API resuelve sesión → usuario → membresía → cuenta activa en una dependencia `require_ctx` aplicada a todos los routers salvo `health`, `auth` y `hooks`. Un 401 de la API hace que el proxy borre la cookie y la web vaya a `/login`.
- **Rationale**: sesiones revocables en servidor (FR-010/011), identidad en cada petición a la API (FR-019), y la base de datos ya está en la API. El middleware Edge de Next solo comprueba presencia y forma de la cookie (no puede consultar la base); la validación real es la de la API en cada petición.
- **Alternatives**: JWT firmado por la web con secreto compartido — no revocable sin lista negra y requiere un secreto nuevo en ambos servicios; NextAuth/Auth.js — trae su propio modelo de sesión en la web, duplicando la identidad que la API necesita.

## D3. Contraseñas con Argon2id

- **Decision**: `argon2-cffi` (Argon2id con los parámetros por defecto de la librería = perfil "low memory" de RFC 9106: t=3, m=64 MiB, p=4, por encima del mínimo OWASP), con rehash automático (`check_needs_rehash`) si cambian los parámetros. Política: mínimo 10 caracteres y lista corta de contraseñas comunes prohibidas (FR-006).
- **Rationale**: estándar actual, una dependencia pequeña y mantenida. `hashlib.scrypt` (stdlib) exigiría ~128 MiB por hash para los parámetros OWASP, caro en la instancia de Railway.
- **Alternatives**: bcrypt (límite de 72 bytes), scrypt stdlib.

## D4. Límite de intentos

- **Decision**: tabla `auth_attempt` (hash del correo, IP, éxito, fecha). Bloqueo de 15 min tras 10 fallos seguidos por correo o 50 por IP en 15 min (SC-007). La IP la pasa la ruta de la web (`X-Forwarded-For` que ve Railway) solo en `/auth/*`, que el proxy genérico no expone (D6).
- **Rationale**: persistente entre reinicios y suficiente para la escala de la beta; sin dependencias.

## D5. Correo transaccional: Resend por HTTP

- **Decision**: puerto `EmailSender` con adaptador **Resend** (`POST https://api.resend.com/emails` vía `httpx`, ya presente) y un adaptador falso para pruebas. Secreto de plataforma `email_api_key`; remitente `StayLever <no-reply@staylever.com>`. Plantillas es/en/pt (verificación, recuperación, "ya tienes cuenta"). Sin clave configurada: el registro por correo muestra "correo no configurado" al administrador y no se crean usuarios por correo (Google sigue funcionando).
- **Rationale**: plan gratis de 3.000 correos/mes (100/día) cubre la beta; API simple; el host verifica el dominio con registros DNS en Cloudflare. Mantiene el principio II (puerto + adaptador).
- **Alternatives**: Brevo (300/día gratis), Amazon SES (más barato a escala, configuración más pesada), SMTP de Gmail (límites y reputación).

## D6. Rutas de acceso dedicadas en la web; el proxy genérico no expone `/auth/*`

- **Decision**: la web tiene rutas propias `/api/auth/{login,register,logout,logout-all,verify,forgot,reset,claim,google/start,google/callback,handoff}` que llaman a la API del lado servidor y ponen/quitan la cookie. El proxy `/api/proxy/*` **rechaza** rutas `auth/*` y `admin/internal*`. Con esto los endpoints sin sesión de la API solo son alcanzables por las rutas de la web.
- **Rationale**: la cookie httpOnly solo puede fijarla la web; la reclamación de la cuenta nº 1 (D9) y el límite por IP dependen de que la llamada venga de la ruta de la web.

## D7. Google: flujo de código con PKCE y estado en servidor; en la app, navegador del sistema + retorno a la app

- **Decision**:
  - **Web**: `/api/auth/google/start?mode=login|register&invite=…` → la API crea un `auth_token` de propósito `oauth_state` (guarda `code_verifier`, modo, código de invitación, cliente, destino; vence en 10 min) y devuelve la URL de Google (`openid email profile`, `prompt=select_account`). `/api/auth/google/callback?code&state` → la API canjea el código en `oauth2.googleapis.com/token` (con secreto de cliente), lee `sub`, `email`, `email_verified`, `name` del `id_token` recibido directamente por TLS del endpoint de tokens (no requiere verificar la firma según la documentación de Google para este canal), busca por `google_sub`, si no por correo verificado (vincula), si no crea (con invitación si el registro está cerrado).
  - **App Android**: Google bloquea su inicio de sesión dentro de vistas web embebidas (`disallowed_useragent`). El botón en la app abre `…/google/start?client=app&challenge=<S256 de un verificador aleatorio>` con **@capacitor/browser** (Custom Tabs). Al terminar, la API emite un **código de traspaso** de un solo uso (2 min) ligado a ese `challenge`, y la web redirige a `com.staylever.app://auth?code=…`. La app (intent-filter del esquema + `App.addListener('appUrlOpen')`) cierra el navegador y lleva el WebView a `/api/auth/handoff?code=…&verifier=…`, que fija la cookie de sesión de 90 días. Requiere **APK 1.1.0**; la versión 1.0.0 oculta el botón de Google y muestra "actualiza la app".
- **Rationale**: RFC 8252 (apps nativas: navegador del sistema + PKCE); el verificador evita que otra app que registre el mismo esquema use un código interceptado. Estado en servidor = funciona aunque el inicio y la vuelta ocurran en navegadores distintos.
- **Alternatives**: plugin nativo de Google Sign-In (Credential Manager) — requiere SHA-1 en Google Cloud por cliente OAuth Android y más código nativo; App Links https verificados — exigen `assetlinks.json` y verificación del dominio; posible mejora futura.

## D8. Invitaciones y registro abierto

- **Decision**: `invite_code` guarda el **hash** del código (formato `SL-XXXX-XXXX`, Crockford base32) y sus últimos 4 caracteres; el código completo se muestra **una sola vez** al crearlo. Consumo atómico (`UPDATE … WHERE used_at IS NULL AND revoked_at IS NULL AND expires_at > now`) dentro de la misma transacción que crea cuenta, usuario y membresía. `platform_setting(key='registration_open')` controla el registro abierto.
- **Rationale**: una filtración de la base no expone códigos usables; dos registros simultáneos con el mismo código → solo uno gana (edge case).

## D9. Migración y reclamación de la cuenta nº 1

- **Decision**: migración Alembic que crea `account` y la fila **id=1** ("Mi cuenta"), añade `account_id` nullable a las tablas, lo rellena con 1 y lo vuelve NOT NULL + FK + índices; ajusta únicos (ver data-model). Idempotente por pasos y reintentable (cada `ALTER` comprueba existencia). La cuenta nº 1 queda **sin usuario**: la ruta web `/api/auth/claim` acepta la contraseña compartida (`APP_PASSWORD`, comparación en tiempo constante) **solo** si la API confirma que la cuenta nº 1 no tiene miembros; entonces crea el usuario dueño con rol de administrador de plataforma. Después la API rechaza toda reclamación y la web deja de usar `APP_PASSWORD` para cualquier otra cosa.
- **Rationale**: no hay que meter datos personales del host en una migración ni secretos nuevos en Railway; quien tiene la contraseña actual es el host. La reclamación no exige verificar el correo (la contraseña compartida ya prueba la identidad y el servicio de correo puede no estar configurado aún); la app muestra "verifica tu correo" cuando se configure.
- **Alternatives**: script manual en Railway (requiere que el host ejecute comandos), sembrar el correo del host en la migración (dato personal en el repo público).

## D10. Secretos: de plataforma y de cuenta

- **Decision**: `secret_entry.account_id` nullable (NULL = plataforma) con dos índices únicos parciales (`name` cuando NULL; `(account_id, name)` cuando no). Catálogo cerrado dividido: plataforma = `openai_api_key`, `anthropic_api_key`, `search_api_key`, `fcm_service_account`, `email_api_key`, `google_oauth_client_id`, `google_oauth_client_secret`; cuenta = `beds24_refresh_token`, `beds24_webhook_key`. La caché en memoria pasa a clave `(account_id|None, name)`. Fallback a variables de entorno **solo** para secretos de plataforma (y, por compatibilidad, para los de la cuenta nº 1 hasta que exista su fila). Rutas: `/settings/secrets` (cuenta) y `/admin/secrets` (plataforma, solo administrador).
- **Rationale**: FR-029; los secretos de plataforma pagan la IA y los avisos de todos.

## D11. Channel manager por cuenta

- **Decision**: `channel_manager_connection` pasa a ser por cuenta (`account_id` único) con `default_prop_ref` y `promo_offer_id` (antes en `settings`). `get_adapter(session)` construye el adaptador con la credencial **de la cuenta del contexto**; sin credencial → `NotConnected` (estado vacío claro, FR-002/US2-5). `property` obtiene `UNIQUE(provider, external_ref)` global (FR-022: una propiedad del channel manager pertenece a una sola cuenta; al importar, si existe en otra cuenta → error claro). Webhook: la clave identifica la cuenta (búsqueda en la caché de secretos de cuenta, comparación en tiempo constante) y el `propertyId` del cuerpo debe ser de esa cuenta. Los ids de Beds24 de la cuenta nº 1 se migran desde `settings` a su conexión en el primer arranque si faltan.
- **Rationale**: principio II intacto (el adaptador no sabe de cuentas; recibe credencial e ids); los `roomId` de Beds24 son únicos globalmente, así que `prop_id` solo hace falta como valor por defecto para precios fijos.

## D12. Tareas programadas por cuenta y datos públicos por ciudad

- **Decision**: `scan_daily` abre una sesión de plataforma para listar cuentas activas con conexión y, **por cada una**, una sesión con su contexto (`tenant_session(account_id)`) dentro de `try/except` que registra el fallo en esa cuenta (`sync_issue`/`intelligence_run`). Eventos y mercado: se agrupan las ciudades de las propiedades activas y cada ciudad se escanea **una vez** (tabla `event` compartida con nueva columna `city` normalizada y único `(city, dedup_key)`; `market_reference` ya es por zona). El prompt del extractor recibe la ciudad (fin de "Medellín" fijo); las sugerencias y la extensión de precios filtran eventos por la ciudad de la propiedad.
- **Rationale**: FR-024/025, SC-005; ahorra costo de IA con varias cuentas en la misma ciudad.

## D13. Entrega incremental (cada PR desplegable)

1. **PR1 — Cuentas y aislamiento** (sin cambio visible): tabla `account`, `account_id` en todo, filtro automático, secretos por ámbito, adaptador/webhook/avisos/cron por cuenta, ciudad en eventos, endpoint de unidades y estados vacíos. La API sigue en modo `AUTH_MODE=legacy` (sin sesión → cuenta nº 1) para desplegar sin cortar el acceso actual.
2. **PR2 — Acceso con correo y sesiones**: usuarios, membresías, sesiones, Argon2, límite de intentos, correo (Resend), verificación, recuperación, reclamación de la cuenta nº 1, cerrar sesión/todas; `AUTH_MODE=sessions` (ya no hay modo legacy).
3. **PR3 — Invitaciones, registro y panel de administrador**: códigos, registro, interruptor, lista/desactivación de cuentas, secretos de plataforma solo para el administrador.
4. **PR4 — Entrar con Google** (web y app) + **APK 1.1.0** (Browser plugin, esquema `com.staylever.app://auth`).

## D14. Pruebas

- `conftest.py`: la fábrica de sesiones crea la cuenta nº 1 y fija su contexto por defecto, de modo que los ~352 tests actuales siguen pasando sin cambios; nuevo fixture `two_accounts` para pruebas de aislamiento.
- `test_tenancy.py`: falla cerrado sin contexto; `session.get`/listados/actualizaciones/borrados no cruzan cuentas; `before_flush` rechaza `account_id` ajeno.
- `test_isolation_*.py`: por cada tipo de dato de FR-013, rutas y herramientas del agente con IDs de la otra cuenta → 404 / "no existe" y cero llamadas al adaptador falso.
- `test_auth.py`: registro, verificación, login, límites, recuperación, sesiones (expiración, revocación, todas), cuenta desactivada, reclamación única.
- `test_google_auth.py`: flujo con transporte HTTP falso (estado, PKCE, vinculación por correo, invitación, traspaso a la app con verificador).
