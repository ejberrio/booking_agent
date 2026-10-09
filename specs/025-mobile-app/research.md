# Research: 025 App móvil

## R1 — Capacitor con la web remota
- **Decisión**: `server.url = "https://staylever.com"`, `server.errorPath = "offline.html"`, `android.allowMixedContent = false`, `appendUserAgent = "StayLeverApp/<versionName>"`. Capacitor inyecta su puente JS en las páginas cargadas, así que los plugins funcionan desde la web remota.
- **Por qué**: la web Next.js es dinámica (SSR + middleware + proxy); exportarla estática exigiría reescribir auth y proxy.
- **Alternativas**: bundle local + API pública (más trabajo y exponer la API); React Native (reescritura).
- **Riesgo App Store (iPhone, futuro)**: guía 4.2 "funcionalidad mínima" penaliza envoltorios web; avisos push nativos y navegación nativa ayudan.

## R2 — Avisos
- **FCM HTTP v1**: `POST https://fcm.googleapis.com/v1/projects/{project_id}/messages:send` con Bearer de una cuenta de servicio. Token OAuth: JWT RS256 (`iss`=client_email, `scope`=`https://www.googleapis.com/auth/firebase.messaging`, `aud`=token_uri, `exp`≤1 h) firmado con `cryptography` y canjeado en `token_uri`; caché hasta 5 min antes de vencer.
- Errores `404 NOT_FOUND`/`UNREGISTERED` o `400 INVALID_ARGUMENT` sobre el token → teléfono desactivado.
- Mensaje: `notification{title,body}` + `data{url}` + `android.notification.channel_id="staylever"`.
- Credenciales: secreto `fcm_service_account` (JSON) en el almacén cifrado (feature 017), con guía.

## R3 — Eventos de reserva
- `sync_service.import_remote(..., events: list | None)`: al crear una reserva → `new`; al cambiar estado a cancelada → `cancelled`; al cambiar fechas → `modified`. Canal y fechas; nunca nombre del huésped.
- Llamadores notifican tras guardar: webhook (`webhook_service.handle`), botón Sincronizar (`/sync/import`), sync diaria (`scan_daily`).
- Dedupe: `push_notification_log` con único (kind, ref, fingerprint).

## R4 — Sugerencias
- `scan_daily`: tras el escaneo, si `run.suggestions_created > 0` → aviso `suggestions` con ref = id del IntelligenceRun.

## R5 — Sesión
- `/api/login`: si el User-Agent contiene `StayLeverApp/` → `createSessionToken(secret, now, 90 días)` y cookie `maxAge` 90 días; si no, 7 días. El middleware ya valida la expiración dentro del token.

## R6 — Firma y CI
- Script del host: `keytool -genkeypair` (JDK de Homebrew, sin sudo) → `gh secret set ANDROID_KEYSTORE_B64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`; `gh secret set GOOGLE_SERVICES_JSON < google-services.json`. Las contraseñas las escribe el host en su terminal.
- Workflow: Java 21 (Temurin), Node 22, `android-actions/setup-android`, `npm ci`, `npx cap sync android`, escribir `google-services.json`, decodificar llave, `./gradlew assembleRelease` (`versionCode` = run_number, `versionName` = tag), artifact + Release en tags `android-v*`.
- Sin secretos de firma → el workflow falla con mensaje claro (no publica un APK sin firmar).

## R7 — Tiendas (documento)
- **Google Play**: cuenta de desarrollador US$25 (pago único), verificación de identidad; para cuentas personales nuevas, prueba cerrada con ≥ 12 testers durante ≥ 14 días antes de producción; política de privacidad pública, formulario de seguridad de datos, target API vigente, AAB en vez de APK.
- **iPhone**: Apple Developer Program US$99/año, Mac con Xcode completo, `npx cap add ios`, APNs key en Firebase, TestFlight para probar, App Review (4.2, cuenta de demostración, privacidad).
