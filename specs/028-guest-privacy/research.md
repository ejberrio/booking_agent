# Research: Privacidad de huéspedes (Feature 028)

## D1. Puerta de aceptación en el servidor
- **Decision**: `require_ctx` consulta si el usuario de la sesión aceptó `LEGAL_VERSION`; si no, responde `403 {"code":"terms_required"}` salvo en rutas permitidas (`/auth/me`, `/auth/terms/accept`, `/auth/logout`, `/auth/logout-all`). En modo `legacy` sin usuario no aplica.
- **Rationale**: la app Android y la web comparten la API; una puerta solo en la interfaz se salta llamando a la API.
- **Alternatives**: middleware de la web (no cubre llamadas directas); comprobar en cada servicio (repetitivo).

## D2. Versión de los documentos
- **Decision**: constante `LEGAL_VERSION = "2026-10-14"` en la API y la misma fecha visible en /terms y /privacy. Publicar una versión = cambiar la constante y los textos en un PR.
- **Alternatives**: tabla editable desde el panel (YAGNI: los textos viven en el código).

## D3. Retención del nombre del huésped
- **Decision**: `UPDATE booking SET guest_name = NULL WHERE check_out < hoy - 365 AND guest_name IS NOT NULL`, por cuenta, dentro del cron diario (`scan_account`), con fallos aislados; y en la sincronización no se guarda el nombre si `check_out < hoy - 365`.
- **Rationale**: el cron ya recorre todas las cuentas con aislamiento de fallos.

## D4. Exportación
- **Decision**: recorrer los modelos `AccountOwned` con el filtro automático de la cuenta y serializar columnas (fechas ISO, decimales como texto, enums por valor); añadir usuario (sin hash), cuenta y aceptaciones. Excluir `secret_entry`, `user_session`, `auth_token`, `auth_attempt`.
- **Rationale**: genérico (si se agrega una tabla de cuenta, entra sola) y seguro (el filtro impide datos ajenos).

## D5. Borrado de cuenta
- **Decision**: en `privacy_service` con sesión de plataforma: para cada tabla de `Base.metadata.sorted_tables` en orden inverso que tenga `account_id` (excepto `account`), `DELETE ... WHERE account_id = :id`; luego secretos de la cuenta, sesiones/tokens/aceptaciones/membresía/usuario; invitaciones usadas quedan con `used_by_account_id` (la cuenta-lápida existe). La cuenta queda `status=deleted`, `name=""`.
- **Rationale**: orden topológico de SQLAlchemy resuelve las FK; la lápida conserva el registro sin datos personales.
- **Identidad**: contraseña si existe; si no (solo Google), código de 6 dígitos por correo, propósito `delete_account`, 15 min, un solo uso, máximo 5 intentos.

## D6. Contenido legal
- **Decision**: /terms nuevo con: partes y objeto, encargo del tratamiento (anfitrión Responsable; StayLever Encargado: solo trata por cuenta del anfitrión, confidencialidad, seguridad, devolución/supresión al terminar), uso aceptable, beta sin garantías, limitación de responsabilidad, terminación, ley aplicable (Colombia), contacto. /privacy agrega retención de 1 año, rol de Encargado, derechos desde Ajustes, copias de seguridad de 7 días.
- **Nota**: revisión por abogado antes de cobrar (F1).
