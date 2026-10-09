# Tasks: Aplicación móvil (Android primero)

**Input**: `/specs/025-mobile-app/`
**Tests**: incluidos (API de avisos, eventos de reserva, dedupe, sesión).

## Phase 1: Setup

- [X] T001 `apps/mobile/`: `package.json` (Capacitor 8.5 core/cli/android/app/push-notifications/device + assets, versiones exactas ≥ 2 semanas), `capacitor.config.ts` (appId `com.staylever.app`, appName StayLever, `server.url` https://staylever.com, `errorPath` offline.html, `appendUserAgent` StayLeverApp/<versión>), `www/index.html` y `www/offline.html` (es/en/pt según el idioma del teléfono, botón reintentar), `.gitignore` (google-services.json, *.keystore, build)
- [X] T002 `npx cap add android`; firma `release` por variables de entorno en `android/app/build.gradle`; `versionCode`/`versionName` desde Gradle properties; canal de avisos "staylever"; icono de notificación; iconos y splash desde el logo (`@capacitor/assets`); plugin google-services condicionado a que exista el archivo
- [X] T003 [P] `.github/workflows/android.yml` (+ `android-check.yml`: APK debug en PRs que tocan apps/mobile) (workflow_dispatch + tags `android-v*`): Java 21, Node 22, Android SDK, `npm ci`, `cap sync`, secretos → google-services.json y keystore, `assembleRelease`, artifact y Release; falla claro sin la llave de firma; SIN `GOOGLE_SERVICES_JSON` construye igual (app sin avisos) y lo advierte
- [X] T004 [P] `scripts/mobile/setup-android-secrets.sh`: verifica `gh`/`keytool` (sugiere `brew install openjdk@21`), crea la llave (contraseñas las escribe el host), carga `ANDROID_KEYSTORE_B64`/`ANDROID_KEYSTORE_PASSWORD`/`ANDROID_KEY_ALIAS`/`ANDROID_KEY_PASSWORD` y `GOOGLE_SERVICES_JSON` con `gh secret set`; nunca imprime valores; guarda la llave fuera del repo

## Phase 2: Foundational (API de avisos)

- [X] T005 Migración `apps/api/migrations/versions/e8f9a0b1c2d3_push.py` + modelos `apps/api/app/models/push.py` (`PushDevice`, `PushNotificationLog`, único kind/ref/fingerprint)
- [X] T006 Puerto `apps/api/app/push/base.py` (`PushMessage`, `PushResult` ok/invalid_token/error, `PushSender`) y adaptador `apps/api/app/push/fcm.py` (JWT RS256 con `cryptography`, token OAuth en caché, `messages:send`, mapeo de errores)
- [X] T007 Secreto `fcm_service_account` en `apps/api/app/services/secret_service.py` (guía Firebase → Configuración → Cuentas de servicio) + prueba de conexión (obtener token OAuth)
- [X] T008 `apps/api/app/services/push_service.py`: registrar/actualizar teléfono, listar, preferencias, quitar; `notify(kind, ref, fingerprint, title, body, url)` con dedupe por log, filtro por preferencia, desactivar token inválido; textos es/en/pt según preferencia de idioma; sin credenciales → no envía y no falla
- [X] T009 Rutas `apps/api/app/api/routes/push.py` (`/push/devices` CRUD, `/push/test`, `/push/status`) + registro en el router
- [X] T010 Tests `apps/api/tests/test_push.py`: upsert/reactivar, preferencias, dedupe, token inválido → desactivado, sin credenciales, FCM con transporte falso (JWT firmado, URL, cuerpo), test endpoint

## Phase 3: US2 + US3 — Avisos de reservas y sugerencias (P1/P2)

- [X] T011 [US2] `sync_service.import_remote(..., events=None)`: `BookingEvent` new/modified/cancelled; `push_service.notify_booking_events` (título/cuerpo con tipo, canal, fechas; url `/calendar?month=`); llamar desde `webhook_service.handle`, `routes/sync.import_remote` y `scripts/scan_daily._sync_channel`
- [X] T012 [US3] `scripts/scan_daily.py`: tras el escaneo, N > 0 → `notify(suggestions, ref=run.id, …, url=/suggestions)`
- [X] T013 [US2] Tests: reserva nueva/cancelada/fechas cambiadas generan eventos; canal/nombre no; dos syncs → un aviso; webhook dispara aviso; sin datos personales en el cuerpo; escaneo con 0 no avisa

## Phase 4: US1 — App instalable (P1)

- [X] T014 [US1] Web `apps/web/lib/native.ts` + `components/native/native-bridge.tsx` (solo dentro de la app): botón atrás (atrás / salir en `/`), registro de avisos tras iniciar sesión (permiso → token → `POST /push/devices` con modelo y versión), tocar aviso → `router.push(url)`; montado en `app/(app)/layout.tsx`; dependencias `@capacitor/core|app|push-notifications|device` en apps/web con import dinámico
- [X] T015 [US1] Sesión 90 días: `apps/web/lib/session.ts` (`createSessionToken(secret, now, maxAge)`), `app/api/login/route.ts` (User-Agent `StayLeverApp/`) + prueba de la función
- [X] T016 [US1] `apps/web/app/(app)/calendar/page.tsx`: `?month=YYYY-MM` abre ese mes

## Phase 5: US4 — Notificaciones en Ajustes (P2)

- [X] T017 [US4] Tarjeta "Notificaciones" en `apps/web/app/(app)/settings/page.tsx`: estado de credenciales (enlace a la guía), teléfonos con plataforma/modelo/último uso, interruptores Reservas/Sugerencias, quitar, "Enviar aviso de prueba"; `lib/api.ts`, `lib/types.ts`; textos es/en/pt

## Phase 6: US5 + Polish

- [X] T018 [US5] `docs/mobile.md`: instalar el APK, configurar Firebase y la llave (script), publicar versión (tag), Google Play (costos, 12 testers × 14 días, privacidad, seguridad de datos, AAB), iPhone (cuenta Apple, Xcode, `cap add ios`, APNs en Firebase, TestFlight, App Review 4.2); recomendación de restringir la clave de API de Firebase al paquete `com.staylever.app` + huella SHA-1 (va dentro del APK)
- [ ] T019 Validación: ruff + pytest; tsc + eslint + build; `cap sync` local; CI construye el APK (con secretos del host) y el host lo instala; aviso de prueba real
- [ ] T020 Producción: migración aplicada; el host configura Firebase y secretos; primera Release `android-v1.0.0`

## Dependencies
T001 → T002 → T003; T004 [P]. T005 → T006 → T007 → T008 → T009 → T010. T011–T013 tras T008. T014–T016 tras T009. T017 tras T009. T018–T020 al final.
