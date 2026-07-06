# Data Model: Feature 017 — Gestión de secretos

**UNA migración** `e2f3a4b5c6d7` (down `d1e2f3a4b5c6`): tablas `secret_entry` y `secret_change_log`. Sin enums de BD nuevos.

## SecretEntry (NUEVA — app/models/secret.py)

| Campo | Tipo | Regla |
|---|---|---|
| id | PK | |
| name | String(60), UNIQUE | de la lista cerrada `SECRET_NAMES` |
| value_encrypted | Text | Fernet(SECRET_KEY-derivada); NUNCA sale de la API (ni cifrado) |
| hint | String(8) | últimos 4 en claro ("…abcd"); vacío si el valor tiene <8 chars |
| created_at / updated_at | TimestampMixin | updated_at = "último cambio" del estado |

`SECRET_NAMES = ["openai_api_key", "anthropic_api_key", "search_api_key", "beds24_refresh_token"]` — coinciden con los atributos de `Settings` (la precedencia BD>env se resuelve por nombre).

## SecretChangeLog (NUEVA)

| Campo | Tipo | Regla |
|---|---|---|
| name | String(60) | |
| action | String(12) | "set" \| "deleted" |
| hint | String(8) | pista del valor NUEVO en "set"; vacío en "deleted" |
| changed_at | DateTime tz | |

Sin valores, jamás. Append-only.

## Caché en memoria (no persistida)

`_cache: dict[name, str | None]` + `_unreadable: set[name]` — cargada del descifrado de `secret_entry` en el lifespan/inicio del scan; write-through en PUT/DELETE. `get_secret(name)` = `_cache[name]` si existe, si no `getattr(settings, name)`.

## Estado de secretos (vista derivada)

Por nombre: `configured` (bool), `source` ("app" | "env" | null), `hint` (de BD si source=app; derivada del env si source=env), `updated_at` (solo app), `unreadable` (bool), `service` (etiqueta de qué apaga si falta: agente / scan / canal).
