# Quickstart / verificación: Feature 026

## Antes de desplegar PR1 (cuentas y aislamiento)
1. Respaldo de la base (`scripts/backup_db.py`) y prueba de la migración sobre una copia: conteos por tabla antes/después idénticos y todo con `account_id = 1`.
2. `uv run pytest` (todos los tests actuales + `test_tenancy.py` + `test_isolation_*.py`).
3. Tras desplegar: el host usa la app como siempre (sigue entrando con la contraseña actual); calendario, sugerencias, chat, ofertas, avisos y webhook funcionan igual.

## Tareas del host (una vez, antes de PR2/PR4)
- **Correo (Resend)**: crear cuenta gratis, añadir el dominio `staylever.com`, copiar los registros DNS a Cloudflare, esperar "Verified", crear una API key y pegarla en StayLever → Administración → Secretos → "Correo (Resend)".
- **Google**: en Google Cloud (proyecto StayLever) → APIs y servicios → Pantalla de consentimiento (externa, nombre StayLever, correo de soporte, ámbitos `openid email profile`, publicar) → Credenciales → ID de cliente OAuth "Aplicación web" con URI de redirección `https://staylever.com/api/auth/google/callback` → pegar ID y secreto en Administración → Secretos.

## PR2 — reclamar la cuenta del host
1. Abrir staylever.com → aparece "Configura tu acceso" (la cuenta nº 1 no tiene usuario).
2. Escribir la contraseña actual, nombre, correo y una contraseña nueva (≥ 10 caracteres) → entra con todos sus datos.
3. Cerrar sesión → entrar con el correo y la contraseña nueva; la contraseña compartida ya no sirve en ninguna pantalla.
4. En la app Android 1.0.0: pide entrar de nuevo (correo y contraseña) y los avisos siguen llegando (Ajustes → Notificaciones → aviso de prueba).
5. "Cerrar todas mis sesiones" en la web → la app pide entrar de nuevo en su siguiente acción.
6. "Olvidé mi contraseña" → llega el correo → cambiarla → las demás sesiones se cierran.

## PR3 — invitar a un anfitrión beta
1. Administración → Invitaciones → "Crear" con nota "Prueba" → copiar el código (se muestra una vez).
2. En una ventana privada: `/register?code=…` → nombre, otro correo, contraseña → llega el correo de verificación → entra a una StayLever **vacía** con el mensaje "Conecta tu channel manager en Ajustes".
3. Con esa cuenta: abrir enlaces del calendario/sugerencias del host cambiando el id en la URL → "no existe"; pedirle al agente "muéstrame la unidad 1" → no la ve.
4. Administración → Cuentas: aparece la cuenta de prueba (sin precios ni reservas). Desactivarla → su sesión queda fuera; reactivarla.
5. Registrarse sin código con el registro cerrado → "beta por invitación".

## PR4 — Google
1. Web: "Entrar con Google" con el correo del host → entra a su cuenta (vinculada).
2. Registro con Google + código en ventana privada → cuenta nueva.
3. Instalar APK 1.1.0 → "Entrar con Google" abre el navegador del sistema → elegir cuenta → vuelve a la app con sesión de 90 días.

## Escaneo con varias cuentas
Con 3 cuentas (una en Cartagena, una con la conexión rota): correr el escaneo (`python -m scripts.scan_daily`) → Medellín y Cartagena escaneadas una vez cada una, sugerencias en cada cuenta, la rota marcada solo en la suya.
