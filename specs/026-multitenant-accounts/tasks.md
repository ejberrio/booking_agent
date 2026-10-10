# Tasks: Multicliente mínimo — cuentas, registro y datos aislados

**Input**: `/specs/026-multitenant-accounts/` (spec, plan, research, data-model, contracts/accounts-api.md, quickstart)
**Tests**: incluidos (el principio VI exige pruebas de aislamiento; el acceso cuesta reputación).
**Entrega**: 4 PRs desplegables (research D13). Cada fase indica su PR.

## Phase 1: Setup (PR1)

- [X] T001 ADR `docs/adr/0007-multitenancy.md` (filtro automático por cuenta, sesiones en la API, secretos por ámbito, Resend, Google PKCE, reclamación, 4 PRs) y actualizar `CLAUDE.md` (ya no "single-tenant")
- [ ] T002 [P] (→ PR2, con T025) Añadir `argon2-cffi` (versión publicada hace > 2 semanas) a `apps/api/pyproject.toml` + `uv lock`

## Phase 2: Foundational — cuentas y filtro automático (PR1, bloquea todo)

- [X] T003 Modelo `apps/api/app/models/account.py`: `Account` (name, status active/disabled, disabled_at, last_seen_at) y mixin `AccountOwned` (`account_id` FK NOT NULL indexado); registrar en `app/models/__init__.py`
- [X] T004 `apps/api/app/db/tenancy.py`: eventos `do_orm_execute` (with_loader_criteria para `AccountOwned`, include_aliases) y `before_flush` (rellena/valida `account_id`), falla cerrado `TenantContextMissing`, `set_tenant(session, account_id, user_id=None)`, `tenant_session(account_id)` y `platform_session()` (bypass explícito) — registrados en `app/db/session.py`
- [X] T005 Aplicar `AccountOwned` a las 28 tablas de data-model.md (`app/models/{property,calendar,booking,audit,availability,pricing,market,agent,push,preference,intelligence,sync,webhook}.py`); `user_id` nullable en logs de auditoría, `agent_action`, `conversation`, `push_device`; nuevos únicos (`booking`, `push_device`, `push_notification_log`, `app_preference`, `scan_config`, `channel_manager_connection`, `property(provider, external_ref)`); `Event.city` + único `(city, dedup_key)`; `ChannelManagerConnection.default_prop_ref/promo_offer_id`; `SecretEntry.account_id`/`SecretChangeLog.account_id` nullable con índices parciales
- [X] T006 Migración `apps/api/migrations/versions/f9a0b1c2d3e4_accounts.py` (down `e8f9a0b1c2d3`): crea `account` + fila 1, añade columnas nullable → backfill 1 (eventos `city='medellin'`; secretos beds24 → cuenta 1, resto NULL) → NOT NULL/FK/índices/únicos; pasos idempotentes; downgrade
- [X] T007 `apps/api/app/core/context.py`: `RequestContext`, dependencia `require_ctx` con `AUTH_MODE=legacy` (sin Bearer → cuenta 1; PR2 la cambia a sesiones) y `require_platform_admin` (legacy: siempre true); aplicar a todos los routers salvo `health`/`hooks` en `app/api/router.py`
- [X] T008 `apps/api/tests/conftest.py`: crear la cuenta 1 y fijar su contexto en la sesión por defecto; fixture `two_accounts` (cuentas A y B con propiedad, unidad, calendario, reservas, sugerencias, promoción, nota, conversación, teléfono)
- [X] T009 Tests `apps/api/tests/test_tenancy.py`: falla cerrado sin contexto; `select`/`session.get`/relaciones/`update`/`delete` no cruzan cuentas; `before_flush` rellena y rechaza `account_id` ajeno; `platform_session` ve todas; solo `admin_service` y `scan_daily` importan `platform_session` (prueba estática)

**Checkpoint**: todos los tests actuales verdes con la cuenta 1 por defecto.

## Phase 3: US3 — Cada cuenta ve y modifica solo lo suyo (P1, PR1)

- [X] T010 [US3] Singletons → por cuenta: `AppPreference` (`preferences.py`, `push_service._lang`), `ScanConfig` (`intelligence_service`), `PricingRule` (`routes/pricing.py`), `ChannelManagerConnection` (`sync_service`), `channel_pricing_service._property`, `status.py` caché por cuenta, `native_deal_service`, `SyncIssue` (todo vía filtro; quitar `id=1` y `.first()` globales)
- [X] T011 [US3] (las rutas `/admin/secrets/*` pasan a PR3/T036; en PR1 `/settings/secrets` muestra los de plataforma solo al administrador) `apps/api/app/services/secret_service.py`: ámbitos plataforma/cuenta (research D10), caché `(account_id|None, name)`, `get_platform_secret`/`get_account_secret`, fallback env solo plataforma (+ cuenta 1 por compatibilidad); `routes/secrets.py` solo secretos de cuenta; nuevas rutas `/admin/secrets/*` (plataforma) en `app/api/routes/admin.py`; secretos nuevos `email_api_key`, `google_oauth_client_id`, `google_oauth_client_secret`
- [X] T012 [US3] (la cuenta nº 1 conserva sus ids de entorno; las demás usan solo roomId — sin migrar settings a la conexión) `apps/api/app/channels/factory.py`: `get_adapter(session)` con la credencial e ids de la cuenta del contexto (`NotConnected` si falta); reemplazar los 15 usos de `routes/sync.get_adapter`; migrar `beds24_prop_id`/`promo_offer_id` de `settings` a la conexión de la cuenta 1 en el arranque si faltan; importación rechaza una propiedad que ya es de otra cuenta (409 claro)
- [X] T013 [US3] Webhook por cuenta: `webhook_service.verify_key` busca la cuenta por clave (tiempo constante), `routes/hooks.py` abre `tenant_session` de esa cuenta, `propertyId` ajeno → ignorado; la URL/clave se muestra por cuenta
- [X] T014 [US3] Avisos por cuenta: `push_service` (registro reasigna el token desde otras cuentas con `platform_session` acotado, envío solo a teléfonos de la cuenta, `user_id`), dedupe por cuenta
- [X] T015 [US3] Agente: `orchestrator` (`_units_context`, `_active_channels` bajo el contexto), `tools.ensure_unit(session, uid)` en lecturas y propuestas (unidad ajena → "no existe", cero llamadas al adaptador), conversación con `user_id`; `routes/chat.py` lista solo conversaciones de la cuenta
- [ ] T016 [US3] (→ PR2: requiere la tabla de usuarios) Auditoría con `user_id` (logs de precio, disponibilidad, promoción, ajuste por canal, secretos) desde el contexto
- [X] T017 [US3] `GET /units` (`apps/api/app/api/routes/units.py`) y `GET/PATCH /account`; web `lib/active-unit.ts` toma la primera unidad de `/units` (no `1` fijo) y `components/empty-state.tsx` en Panorama/Calendario/Sugerencias/Ofertas cuando no hay unidades o conexión (es/en/pt)
- [X] T018 [P] [US3] Tests `apps/api/tests/test_isolation_routes.py`: con `two_accounts`, cada ruta de datos de B con ids de A → 404 o lista sin datos de A; escrituras (preview/apply de precios, disponibilidad, promociones, notas, sugerencias, push) sobre recursos de A → 404 y adaptador falso sin llamadas
- [X] T019 [P] [US3] Tests `apps/api/tests/test_isolation_agent.py`: herramientas de lectura y propuestas del agente de B con `unit_type_id`/`promotion_id`/`change_id` de A → "no existe"; contexto del prompt sin unidades de A; confirmar una acción de otra cuenta → no existe
- [X] T020 [P] [US3] Tests `apps/api/tests/test_isolation_jobs.py`: webhook con clave de A solo toca A; clave desconocida → 401; propiedad de otra cuenta ignorada; avisos solo a teléfonos de la cuenta; secretos de cuenta no visibles desde otra; importar propiedad de otra cuenta → 409

## Phase 4: US6 — Cada cuenta con su ciudad (P3, PR1)

- [X] T021 [US6] `app/market/extractor.py` y `tavily_market.py` reciben la ciudad (sin "Medellín" fijo); `event_service.upsert_event(city=…)` con `normalize_city`; `suggestion_engine` y `price_extension_service` filtran eventos por la ciudad de la propiedad
- [X] T022 [US6] `intelligence_service`: separar `scan_city(city)` (eventos + mercado, una vez por ciudad) de `suggest_for_account()`; `scripts/scan_daily.py` recorre cuentas activas con conexión (`platform_session` para listar, `tenant_session` por cuenta, `try/except` que registra el fallo en esa cuenta), ciudades únicas una vez; `prompts.py`/`tools.py`/`texts.py` con ciudad y moneda de la propiedad
- [X] T023 [P] [US6] Tests `apps/api/tests/test_scan_multi.py`: 3 cuentas (Medellín, Cartagena, conexión rota) → cada ciudad escaneada una vez, sugerencias por cuenta, la rota marcada solo en la suya; eventos de Cartagena no afectan sugerencias de Medellín

**Checkpoint PR1**: desplegable sin cambio visible (`AUTH_MODE=legacy`). Verificar quickstart "Antes de desplegar PR1".

## Phase 5: US1 + US4 — Reclamar la cuenta y entrar con correo (P1/P2, PR2)

- [ ] T024 [US1] Modelos `apps/api/app/models/auth.py` (`AppUser`, `Membership`, `UserSession`, `AuthToken`, `AuthAttempt`) + migración `a1b2c3d4e5f7_auth.py`
- [ ] T025 [US4] `apps/api/app/auth/passwords.py` (Argon2id, rehash, política ≥ 10 y lista de comunes), `tokens.py` (token aleatorio + sha256, enlaces de un solo uso), `ratelimit.py` (10 fallos/correo, 50/IP en 15 min)
- [ ] T026 [P] [US4] Puerto de correo `apps/api/app/email/{base,resend,fake}.py` + plantillas es/en/pt (`templates.py`: verificación, recuperación, "ya tienes cuenta")
- [ ] T027 [US4] `apps/api/app/services/auth_service.py`: login, sesiones (crear/validar/revocar/todas, `last_used_at` cada 5 min, `account.last_seen_at`), verificación, reenvío, olvidé/restablecer (revoca sesiones), `me`; `claim_status`/`claim` (solo cuenta 1 sin miembros → dueño + `is_platform_admin`)
- [ ] T028 [US4] Rutas `apps/api/app/api/routes/auth.py` (contrato) y `require_ctx` en modo sesiones (Bearer → sesión → usuario → membresía → cuenta activa; 401/403); quitar `AUTH_MODE=legacy`
- [ ] T029 [US1] Web: `lib/session.ts` (cookie `sl_session`, duraciones), `middleware.ts` (forma de la cookie, rutas públicas), proxy (Bearer desde cookie, bloquea `auth/*`, ignora cabeceras de identidad del navegador, borra cookie en 401), `lib/api.ts` (401 → `/login?next=`), eliminar `app/api/login` antiguo
- [ ] T030 [US1] Web: rutas `app/api/auth/{login,logout,logout-all,verify,forgot,reset,claim}/route.ts` (claim compara `APP_PASSWORD` en tiempo constante y solo si `claim-status`)
- [ ] T031 [US4] Web: páginas `app/(auth)/{login,forgot,reset,verify,claim}/page.tsx` (es/en/pt, tema claro/oscuro, mensajes genéricos, "reenviar verificación"); `/login` redirige a `/claim` si la cuenta 1 es reclamable
- [ ] T032 [US4] Ajustes → "Mi cuenta": nombre de la cuenta, correo, verificar correo, cambiar contraseña, "cerrar todas mis sesiones", cerrar sesión (menú)
- [ ] T033 [P] [US4] Tests `apps/api/tests/test_auth.py`: login ok/incorrecto genérico/bloqueo tras 10 fallos; correo sin verificar → 403; verificación de un solo uso y vencida; recuperación revoca sesiones; logout y logout-all; sesión web 7 días / app 90 días; cuenta desactivada → 401; claim una sola vez y luego 409; rutas sin Bearer → 401

**Checkpoint PR2**: el host reclama su cuenta (quickstart PR2).

## Phase 6: US2 + US5 — Invitaciones, registro y panel de administrador (P1/P2, PR3)

- [ ] T034 [US2] Modelos `InviteCode` y `PlatformSetting` + migración `b2c3d4e5f6a8_invites.py`
- [ ] T035 [US2] `apps/api/app/services/invite_service.py` (crear `SL-XXXX-XXXX` con hash + last4, listar estados, revocar, consumo atómico) y `auth_service.register` (código requerido si el registro está cerrado; crea cuenta + usuario + membresía dueño en una transacción; correo existente → "ya tienes cuenta" sin consumir el código; 503 sin correo configurado)
- [ ] T036 [US5] `apps/api/app/services/admin_service.py` + `routes/admin.py`: invitaciones, cuentas (sin datos privados; desactivar revoca sesiones; no la propia), `registration_open`, `llm-config`, secretos de plataforma — todo con `require_platform_admin`
- [ ] T037 [US2] Web: `app/api/auth/register/route.ts` + página `app/(auth)/register/page.tsx` (`?code=`), mensaje "beta por invitación"
- [ ] T038 [US5] Web: `app/(app)/admin/page.tsx` (Invitaciones con copiar código una vez, Cuentas, Registro abierto, Secretos de plataforma, Modelo de IA) y enlace en el menú solo para administradores; Ajustes ya no muestra secretos de plataforma
- [ ] T039 [P] [US2] Tests `apps/api/tests/test_invites_admin.py`: código vigente/usado/vencido/revocado; doble uso simultáneo → uno gana; registro cerrado sin código → 400; abierto sin código → ok; correo existente no consume; admin vs no admin (403); lista de cuentas sin datos privados; desactivar/reactivar; cuenta nueva vacía sin errores en `/status`, `/units`, calendario, sugerencias

**Checkpoint PR3**: invitar a un anfitrión beta (quickstart PR3).

## Phase 7: US4 — Entrar con Google en web y app (P2, PR4)

- [ ] T040 [US4] `apps/api/app/services/google_auth_service.py`: `start` (estado en `auth_token` con verificador PKCE, modo, invitación, cliente, challenge de la app), `callback` (canje del código con transporte inyectable, lectura de `sub/email/email_verified/name`, vincular por `google_sub` o correo verificado, crear con invitación), `handoff` (código de 2 min ligado al challenge S256) + rutas en `routes/auth.py`
- [ ] T041 [US4] Web: `app/api/auth/google/{start,callback}/route.ts`, `app/api/auth/handoff/route.ts`; botón "Entrar con Google" en login/registro (oculto sin credenciales; en app < 1.1.0 muestra "actualiza la app")
- [ ] T042 [US4] App 1.1.0: `@capacitor/browser` en `apps/mobile` y `apps/web`, intent-filter `com.staylever.app://auth` en `AndroidManifest.xml`, `native-bridge.tsx` (abrir Google en el navegador del sistema con verificador, `appUrlOpen` → cerrar navegador → `/api/auth/handoff`), publicar `android-v1.1.0`
- [ ] T043 [P] [US4] Tests `apps/api/tests/test_google_auth.py`: estado inválido/vencido; PKCE; vincula por correo verificado; correo no verificado no vincula; registro requiere invitación con registro cerrado; handoff con verificador correcto/incorrecto/reusado

## Phase 8: Polish

- [ ] T044 [P] `docs/accounts.md` (reclamar la cuenta, configurar Resend y Google, invitar, administrar, desactivar) + `docs/operations.md` (cron por cuenta) + `docs/mobile.md` (APK 1.1.0)
- [ ] T045 Revisión de logs: sin correos completos, tokens ni datos de huéspedes; `ruff`, `pytest`, `tsc`, `eslint`, `build` verdes
- [ ] T046 Verificación en producción con el host (quickstart completo) y cierre de #143

## Dependencies

- Phase 2 bloquea todo. US3 (Phase 3) y US6 (Phase 4) completan PR1.
- PR2 (Phase 5) depende de PR1. PR3 (Phase 6) depende de PR2. PR4 (Phase 7) depende de PR2 (y de PR3 para registro con Google + invitación).
- Tareas del host antes de PR2/PR4: Resend y cliente OAuth de Google (quickstart).

## Parallel opportunities

- T002 con T003–T006. T018/T019/T020 en paralelo tras T010–T017. T023 tras T022. T026 en paralelo con T025. Tests de cada fase en paralelo con la web de esa fase.

## Implementation strategy

MVP = PR1 + PR2 (aislamiento real y acceso por usuario: el host sigue operando y la base está lista). PR3 abre la beta (invitaciones). PR4 añade comodidad (Google) y el APK 1.1.0.
