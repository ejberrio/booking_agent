# Data Model: Multicliente mínimo (Feature 026)

## Tablas nuevas

### `account` (PR1)
| Campo | Tipo | Notas |
|---|---|---|
| id | int PK | la fila **1** se crea en la migración ("Mi cuenta") con todos los datos actuales |
| name | str(120) | nombre visible de la cuenta |
| status | enum `active` \| `disabled` | desactivada: sin acceso, el cron la omite, datos intactos |
| disabled_at | datetime? | |
| last_seen_at | datetime? | último uso de cualquier sesión de la cuenta (para el panel) |
| created_at / updated_at | datetime | `TimestampMixin` |

### `app_user` (PR2)
| Campo | Tipo | Notas |
|---|---|---|
| id | int PK | |
| email | str(254) | **único**, guardado en minúsculas y sin espacios |
| name | str(120) | |
| password_hash | str? | Argon2id; NULL si solo entra con Google |
| google_sub | str(64)? | **único**; identidad de Google |
| email_verified_at | datetime? | NULL = sin verificar (bloquea el acceso salvo la reclamación de la cuenta nº 1) |
| language | str(2) | es/en/pt (correos) |
| is_platform_admin | bool | el host (al reclamar la cuenta nº 1) |
| last_login_at | datetime? | |

### `membership` (PR2)
`id`, `user_id` FK, `account_id` FK, `role` (`owner`; preparado para `member`), único `(user_id, account_id)`. En esta versión cada usuario tiene exactamente una membresía y cada cuenta un dueño.

### `user_session` (PR2)
`id`, `user_id` FK, `token_hash` (sha256 hex, **único**), `kind` (`web` 7 días \| `app` 90 días), `created_at`, `expires_at`, `last_used_at` (se actualiza como mucho cada 5 min), `revoked_at`, `user_agent` (recortado, sin IP). Válida si `revoked_at IS NULL AND expires_at > now` y la cuenta está activa.

### `auth_token` (PR2/PR4)
Enlaces y estados de un solo uso. `id`, `purpose` (`verify_email` 24 h \| `reset_password` 1 h \| `oauth_state` 10 min \| `app_handoff` 2 min), `token_hash` único, `user_id`?, `payload` JSON (p. ej. `code_verifier`, modo, invitación, `challenge` de la app), `expires_at`, `used_at`.

### `auth_attempt` (PR2)
`id`, `email_hash` (sha256 del correo normalizado), `ip` (str, solo para el límite; se purgan > 7 días), `success` bool, `created_at`. Índices `(email_hash, created_at)`, `(ip, created_at)`.

### `invite_code` (PR3)
`id`, `code_hash` único, `last4`, `note` str(200)?, `expires_at` (por defecto +30 días), `created_by_user_id`, `used_at`?, `used_by_account_id`?, `revoked_at`?. Estado derivado: vigente / usado / vencido / revocado.

### `platform_setting` (PR3)
`key` PK str(64), `value` JSON. Claves: `registration_open` (bool, por defecto false).

## Tablas existentes que pasan a ser de una cuenta (mixin `AccountOwned`: `account_id` FK NOT NULL indexado)

`property`, `unit_type`, `channel`, `calendar_day`, `rate`, `calendar_note`, `booking`, `price_change_log`, `availability_change_log`, `promotion`, `promotion_change_log`, `channel_offset_log`, `pricing_rule`, `native_deal`, `price_suggestion`, `point_of_interest`, `conversation`, `message`, `agent_action`, `push_device`, `push_notification_log`, `app_preference`, `scan_config`, `intelligence_run`, `sync_run`, `sync_issue`, `webhook_event`, `channel_manager_connection`.

Migración: añadir nullable → `UPDATE … SET account_id = 1` → NOT NULL + FK + índice. Filtro automático en lecturas/escrituras del ORM (research D1).

### Cambios de unicidad y campos
| Tabla | Antes | Después |
|---|---|---|
| `booking` | `external_ref` único global | único `(account_id, external_ref)` |
| `push_device` | `token` único global | único `(account_id, token)`; al registrar un token en una cuenta se borra de las demás (el teléfono pertenece a la sesión actual); + `user_id` FK nullable (quién lo registró) |
| `push_notification_log` | único `(kind, ref, fingerprint)` | único `(account_id, kind, ref, fingerprint)` |
| `app_preference` | singleton `id=1` | una fila por cuenta (único `account_id`); se crea con valores por defecto si falta |
| `scan_config` | primera fila | una por cuenta (único `account_id`) |
| `channel_manager_connection` | "una activa" global | una por cuenta (único `account_id`) + `default_prop_ref`, `promo_offer_id` (antes en `settings`) |
| `property` | `external_ref` sin unicidad | único `(provider, external_ref)` global — una propiedad del channel manager pertenece a una sola cuenta (FR-022); `provider` = `beds24` para las actuales |
| `price_change_log`, `availability_change_log`, `promotion_change_log`, `channel_offset_log`, `secret_change_log` | origen sin usuario | + `user_id` FK nullable (quién; NULL = sistema/cron) |
| `agent_action` | — | + `user_id` nullable (quién confirmó) |
| `conversation` | sin dueño | + `user_id` nullable (quién la creó) |

## Tablas de plataforma (sin `account_id`, compartidas)

| Tabla | Uso |
|---|---|
| `event` | eventos públicos por ciudad: + `city` (normalizada: minúsculas, sin tildes; filas actuales → `medellin`); único `(city, dedup_key)` en lugar de `dedup_key` |
| `market_reference` | referencias de mercado por zona (ya es por zona) |
| `llm_config` | configuración del modelo de IA (plataforma) |
| `secret_entry` | `account_id` **nullable**: NULL = secreto de plataforma; índices únicos parciales `name WHERE account_id IS NULL` y `(account_id, name) WHERE account_id IS NOT NULL`; filas actuales `beds24_refresh_token`/`beds24_webhook_key` → cuenta 1, el resto → plataforma. No usa el filtro automático: `secret_service` filtra explícitamente |
| `secret_change_log` | + `account_id` nullable (mismo criterio) |

## Contexto de petición

`RequestContext(account_id, user_id | None, is_platform_admin, session_kind)` — derivado **solo** de la sesión (o de la clave del webhook, o del recorrido del cron). Se guarda en `session.info["account_id"]`/`["user_id"]`. `session.info["platform"] = True` habilita consultas entre cuentas **solo** en `admin_service` y en el recorrido del cron (listar cuentas/ciudades).

## Reglas de validación

- Correo: normalizado, formato válido, ≤ 254; contraseña ≥ 10 caracteres y no en la lista de comunes.
- Código de invitación: vigente = no usado, no revocado, no vencido; consumo atómico.
- Una sesión de una cuenta desactivada es inválida aunque no esté revocada.
- `account_id` de un objeto nuevo = el del contexto; distinto → error (nunca se "mueve" un dato de cuenta).
