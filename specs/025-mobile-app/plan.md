# Implementation Plan: Aplicación móvil (Android primero, iPhone después)

**Branch**: `025-mobile-app` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/025-mobile-app/spec.md` · issue #140

## Summary

Nuevo paquete `apps/mobile`: proyecto **Capacitor 8** (Android) que carga **https://staylever.com** en un WebView nativo (`server.url`), con página local de "sin conexión" (`server.errorPath`), icono/splash StayLever, agente de usuario `StayLeverApp/<versión>`, y plugins nativos **App** (botón atrás), **Push Notifications** (Firebase Cloud Messaging) y **Device**. La web detecta que corre dentro de la app y activa: registro del teléfono para avisos, navegación al tocar un aviso y botón atrás. La sesión creada desde la app dura **90 días**. En la API: tablas de teléfonos y de avisos enviados, puerto `PushSender` con implementación **FCM HTTP v1** (firma JWT con `cryptography`, sin dependencias nuevas), avisos de **reservas** (desde la sincronización entrante, usada por el webhook, el botón Sincronizar y la sync diaria) y de **sugerencias** (escaneo diario), con deduplicación. El APK se construye en **GitHub Actions** con llave de firma y `google-services.json` desde **secretos de GitHub** (repo público) y se publica como **Release** descargable. Documento con requisitos de Google Play y del camino a iPhone.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (web), Capacitor 8.5 (Android, Java 21 / Gradle en CI)
**Primary Dependencies**: nuevas solo en JS: `@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, `@capacitor/app`, `@capacitor/push-notifications`, `@capacitor/device`, `@capacitor/assets` (dev) — versiones exactas publicadas hace ≥ 2 semanas. Python: ninguna (FCM con `httpx` + `cryptography` ya presentes).
**Storage**: migración `e8f9a0b1c2d3` (down `d7e8f9a0b1c2`): `push_device`, `push_notification_log`.
**Testing**: pytest (registro de teléfonos, preferencias, deduplicación, eventos de reserva desde la sync, aviso de sugerencias, token inválido → desactivado, FCM con transporte falso, sesión 90 días en web); web tsc/eslint/build; CI construye el APK; prueba real en el Android del host.
**Target Platform**: Railway (API + web), Android 8+ (minSdk de Capacitor 8), iPhone: preparado, no construido.
**Project Type**: monorepo web + mobile
**Constraints**: repo público → ningún secreto versionado; Principio III intacto (los avisos solo informan); sin datos personales del huésped en avisos ni logs; es/en/pt; no romper 344 tests.

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ 4 decisiones del host registradas |
| II. Provider-agnostic | ✅ puerto `PushSender` (FCM es un adaptador); avisos de reserva desde la sync neutral, no desde Beds24 |
| III. Human-in-the-loop | ✅ la app es la misma web: toda escritura sigue con vista previa + confirmación; los avisos no escriben |
| IV. Tipado y pruebas | ✅ servicio de avisos, dedupe y eventos con tests; FCM con transporte falso |
| V. Simplicidad | ✅ una sola interfaz (la web); sin dependencias Python nuevas; build en CI sin instalar nada en el Mac |

**Post-diseño (re-check)**: ✅ sin violaciones.

## Project Structure

```text
specs/025-mobile-app/ (spec, plan, research, data-model, quickstart, contracts/push-api.md, tasks)

apps/mobile/                         # NUEVO
├── package.json · capacitor.config.ts   # appId com.staylever.app, server.url, errorPath, appendUserAgent
├── www/index.html · www/offline.html    # página local mínima + "sin conexión / reintentar"
├── resources/icon.png · splash.png      # generados desde el logo
└── android/                              # proyecto nativo (cap add android), firma por variables de entorno

.github/workflows/android.yml        # NUEVO: build APK firmado → artifact + Release (tag android-v*)
scripts/mobile/setup-android-secrets.sh  # NUEVO: el host crea la llave y carga secretos con gh (yo no veo valores)

apps/api/
├── app/models/push.py                       # PushDevice, PushNotificationLog
├── migrations/versions/e8f9a0b1c2d3_push.py
├── app/push/{__init__,base,fcm}.py          # puerto PushSender + adaptador FCM HTTP v1
├── app/services/push_service.py             # registrar, preferencias, enviar con dedupe, textos es/en/pt
├── app/services/sync_service.py             # import_remote(..., events=) → eventos de reserva
├── app/services/webhook_service.py · app/api/routes/sync.py · scripts/scan_daily.py  # notifican
├── app/services/secret_service.py           # secreto `fcm_service_account` + prueba
├── app/api/routes/push.py                   # /push/devices, /push/test, /push/status
└── tests/test_push.py

apps/web/
├── lib/native.ts                     # ¿app nativa? plugins por import dinámico
├── components/native/native-bridge.tsx   # botón atrás, registro push, tap en aviso → ruta
├── app/(app)/layout.tsx              # monta NativeBridge
├── app/api/login/route.ts · lib/session.ts   # 90 días si User-Agent StayLeverApp
├── app/(app)/settings/page.tsx       # tarjeta "Notificaciones"
├── app/(app)/calendar/page.tsx       # ?month=YYYY-MM
├── lib/{api,types}.ts · catalog settings/shell (es/en/pt)
docs/mobile.md                        # instalar APK, configurar Firebase/llave, Google Play, iPhone
```

## Decisiones clave (detalle en research.md)

1. **WebView remoto** (`server.url`): la web es SSR (no exportable estática); una sola interfaz; actualizaciones de la web llegan sin reinstalar.
2. **Avisos**: FCM (gratis; también sirve para iPhone vía APNs más adelante). Token del teléfono → `push_device`.
3. **Firma**: llave creada por el host (script con `keytool` + `gh secret set`); CI firma `assembleRelease`. Debug nunca se publica.
4. **Sesión 90 días**: `appendUserAgent: "StayLeverApp/x"` → `/api/login` emite token de 90 días.
5. **Eventos de reserva**: `import_remote` reporta new/modified/cancelled; huella `estado:check_in:check_out`; `push_notification_log` único (kind, ref, huella).
6. **Distribución**: GitHub Release `android-vX.Y.Z` con el APK (repo público: el APK no contiene secretos privados; `google-services.json` es configuración cliente de Firebase).

## Complexity Tracking

Sin violaciones.
