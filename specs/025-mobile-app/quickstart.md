# Quickstart: 025

```bash
cd apps/api && uv run pytest -q tests/test_push.py
cd apps/web && npx tsc --noEmit && npm run lint && npm run build
cd apps/mobile && npm ci && npx cap sync android   # en CI: ./gradlew assembleRelease
```

Host (una vez): Firebase (proyecto gratis + app Android `com.staylever.app` → `google-services.json` y llave de cuenta de servicio), `scripts/mobile/setup-android-secrets.sh`, pegar la cuenta de servicio en Ajustes → Credenciales de avisos.

1. GitHub → Actions → "Android APK" (o tag `android-v1.0.0`) → Release con `StayLever-1.0.0.apk`.
2. En el Android: descargar, permitir origen desconocido, instalar, abrir, iniciar sesión, permitir avisos.
3. Ajustes → Notificaciones: aparece el teléfono → "Enviar aviso de prueba" → llega.
4. Reserva de prueba / webhook → aviso "Nueva reserva…"; tocar → Calendario del mes.
5. Escaneo con sugerencias nuevas → aviso → Sugerencias.
6. Botón atrás, enlaces externos al navegador, modo avión → "sin conexión".
