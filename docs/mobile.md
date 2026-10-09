# App móvil de StayLever (Feature 025 · issue #140)

La app es un contenedor nativo (**Capacitor 8**) que abre **staylever.com** a pantalla completa, con icono propio, botón atrás de Android, página "sin conexión" y **avisos** (reservas y sugerencias). Toda la funcionalidad es la de la web: cuando la web mejora, la app mejora sin reinstalar (solo cambios nativos requieren un APK nuevo).

- Código: `apps/mobile` (proyecto Android en `apps/mobile/android`).
- Sesión: 90 días dentro de la app (la web sigue en 7). Cerrar sesión o cambiar `APP_PASSWORD` la invalida.
- Avisos: Firebase Cloud Messaging (gratis). Ajustes → **Notificaciones en el celular** muestra teléfonos, interruptores y "Enviar aviso de prueba".

## 1. Preparación (una sola vez)

> El repositorio es **público**: la llave de firma y los archivos de Firebase **nunca** van al código. Se cargan como secretos.

### 1.1 Firebase (avisos) — opcional pero recomendado
1. https://console.firebase.google.com → **Agregar proyecto** (p. ej. "StayLever"; Analytics no es necesario).
2. En el proyecto: **Agregar app → Android**. Nombre del paquete: `com.staylever.app`. Descarga **google-services.json** (guárdalo fuera del repo).
3. **⚙️ Configuración del proyecto → Cuentas de servicio → Generar nueva clave privada** → se descarga un `.json` (es SECRETO).
4. En StayLever: **Ajustes → Secretos → "Credencial de avisos (Firebase)"** → pega TODO el contenido de ese `.json` → **Guardar** → **Probar** (debe decir "Firebase OK").

### 1.2 Llave de firma + secretos de GitHub
Requisitos en el Mac: `brew install gh openjdk@21` y `gh auth login` (cuenta `ejberrio`).

```bash
bash scripts/mobile/setup-android-secrets.sh ~/Downloads/google-services.json
```

- Crea la llave en `~/.staylever/staylever-release.keystore` (fuera del repo) con la contraseña que tú escribes.
- **Haz copia de seguridad de esa llave y su contraseña** (gestor de contraseñas): sin ellas no podrás actualizar la app instalada ni publicarla en Play Store.
- Carga en GitHub: `ANDROID_KEYSTORE_B64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` y `GOOGLE_SERVICES_JSON`.
- Sin `google-services.json` el APK se construye igual, pero **sin avisos**.

### 1.3 Restringir la clave de Firebase (recomendado)
`google-services.json` queda dentro del APK (es configuración de cliente). En https://console.cloud.google.com → **APIs y servicios → Credenciales** → la "Android key" del proyecto → **Restricción de aplicaciones: Android** → paquete `com.staylever.app` + **huella SHA-1** (la imprime el script).

## 2. Publicar una versión
- GitHub → **Actions → Android APK → Run workflow** → versión `1.0.0`, o bien un tag: `git tag android-v1.0.1 && git push origin android-v1.0.1`.
- El workflow firma el APK y crea el Release **"StayLever Android X.Y.Z"** (pre-release) con `StayLever-X.Y.Z.apk`.
- Cada PR que toca `apps/mobile` compila un APK de prueba (workflow "Android check") para detectar errores antes.

## 3. Instalar en el Android (sin Play Store)
1. En el celular abre el Release (https://github.com/ejberrio/booking_agent/releases) y descarga el `.apk`.
2. Ábrelo. Si Android lo pide: **Configuración → Instalar apps desconocidas** → permite al navegador / "Archivos".
3. Instala → abre **StayLever** → inicia sesión → **permite los avisos**.
4. Ajustes → Notificaciones en el celular → aparece tu teléfono → **Enviar aviso de prueba**.

Play Protect puede advertir "app de un desarrollador desconocido": es normal fuera de la tienda; elige "Instalar de todos modos". Las actualizaciones se instalan encima (misma llave) sin perder la sesión.

## 4. Google Play (cuando decidas publicar)
- Cuenta de desarrollador: **US$25 pago único**, verificación de identidad (y de dirección/teléfono).
- Cuentas personales nuevas: **prueba cerrada con ≥ 12 testers durante ≥ 14 días seguidos** antes de pedir producción.
- Requisitos de la ficha: política de privacidad pública (URL), formulario de **Seguridad de los datos**, clasificación de contenido, capturas, icono 512 px, gráfico destacado 1024×500.
- Formato: Google Play pide **AAB** (`./gradlew bundleRelease`) y "Play App Signing" (se sube la llave de subida = la de `~/.staylever`).
- Target API: la exigida por Google en el momento (Capacitor 8 apunta a API 36).
- Revisión: apps que solo envuelven una web pueden ser observadas; los avisos y la navegación nativa ayudan. Proveer una cuenta de prueba para el revisor.

## 5. iPhone (cuando tengas la cuenta de Apple)
- **Apple Developer Program: US$99/año** (necesario incluso para instalarla en tu propio iPhone de forma estable).
- Mac con **Xcode completo** (App Store) — hoy el Mac solo tiene Command Line Tools.
- Pasos técnicos pendientes:
  1. `cd apps/mobile && npm i @capacitor/ios@8.5.x && npx cap add ios` (fijar versión ≥ 2 semanas).
  2. En Apple Developer: identificador `com.staylever.app` con **Push Notifications**; crear una **APNs Auth Key (.p8)** y subirla a Firebase (Configuración → Cloud Messaging → app de Apple).
  3. Agregar `GoogleService-Info.plist` (Firebase → app iOS) sin versionarlo (repo público).
  4. Xcode: firma con tu equipo, capacidad Push Notifications + Background Modes (remote notifications).
  5. Probar con **TestFlight**; luego enviar a revisión.
- App Review: guía **4.2 "funcionalidad mínima"** (envoltorios de web) → destacar avisos nativos; cuenta de demostración; política de privacidad; **iOS no permite APK**: fuera de TestFlight/App Store solo vía distribución de empresa (no aplica).

## 6. Cómo funciona por dentro
- `apps/mobile/capacitor.config.ts`: `server.url = https://staylever.com`, `errorPath = offline.html`, User-Agent `StayLeverApp/<versión>` (+ ` push` si el APK incluye Firebase).
- Web: `components/native/native-bridge.tsx` (solo dentro de la app): botón atrás, permiso y registro de avisos (`POST /push/devices`), tocar un aviso abre su pantalla (`/calendar?month=…`, `/suggestions`).
- API: `push_service` envía con deduplicación (`push_notification_log`), desactiva teléfonos con token inválido; avisos de reservas desde la sincronización entrante (webhook de Beds24, botón Sincronizar, sync diaria) y de sugerencias desde el escaneo diario. Los avisos nunca llevan el nombre del huésped.
