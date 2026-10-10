# Implementation Plan: Multicliente mínimo — cuentas, registro y datos aislados

**Branch**: `026-multitenant-accounts` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/026-multitenant-accounts/spec.md` · issue #143 · épica #156

## Summary

StayLever pasa de una herramienta personal a **varias cuentas aisladas**. Cada dato del anfitrión lleva `account_id` y un **filtro automático del ORM** (SQLAlchemy `do_orm_execute` + `with_loader_criteria`, `before_flush`, falla cerrado sin contexto) garantiza que ninguna ruta, tarea programada ni herramienta del agente cruce cuentas. La **identidad vive en la API**: usuarios, contraseñas Argon2id y sesiones opacas revocables (hash en base de datos; 7 días web / 90 días app); la web guarda la cookie `sl_session` y el proxy la convierte en `Authorization: Bearer`; la API exige sesión en todo salvo `health`, `auth` y `hooks`. Registro **solo con código de invitación** (interruptor para abrirlo), verificación y recuperación por **correo (Resend)**, **Entrar con Google** (código + PKCE con estado en servidor; en Android por navegador del sistema y retorno a la app → **APK 1.1.0**). Panel de **administrador de plataforma** (invitaciones, cuentas, registro abierto, secretos de plataforma). Secretos separados en plataforma/cuenta; adaptador de Beds24, webhook, avisos y cron **por cuenta**; eventos y mercado **por ciudad** compartidos. Migración: todo a la **cuenta nº 1**, que el host reclama con la contraseña actual. Entrega en **4 PRs desplegables** (research D13).

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (web), Capacitor 8.5 (Android)
**Primary Dependencies**: nueva en Python: `argon2-cffi` (≥ 23.1, publicada hace > 2 semanas). Correo y Google por `httpx` (ya presente). Nueva en JS (app): `@capacitor/browser` 8.x (versión exacta publicada hace ≥ 2 semanas).
**Storage**: PostgreSQL. Migraciones (cadena lineal desde `e8f9a0b1c2d3`): `f9a0b1c2d3e4_accounts` (PR1), `a1b2c3d4e5f7_auth` (PR2), `b2c3d4e5f6a8_invites` (PR3). Ver data-model.md.
**Testing**: pytest (SQLite en memoria; `conftest` crea la cuenta nº 1 y fija su contexto por defecto → los tests actuales no cambian); nuevos `test_tenancy.py`, `test_isolation_*.py`, `test_auth.py`, `test_invites_admin.py`, `test_google_auth.py`, `test_scan_multi.py`; web `tsc`/`eslint`/`build`; CI Android check; verificación manual con quickstart.md.
**Target Platform**: Railway (API privada + web pública staylever.com), Android 7+ (APK 1.1.0).
**Project Type**: monorepo web + API + mobile
**Performance Goals**: validar la sesión añade 1 consulta indexada por petición (< 5 ms); escaneo diario lineal en nº de cuentas, eventos/mercado una vez por ciudad.
**Constraints**: principio VI (aislamiento) y III (confirmación) no negociables; repo público (secretos solo en la app/Railway por el host); sin datos personales en logs; es/en/pt; tema claro/oscuro; no romper ~352 tests; el host no pierde datos.
**Scale/Scope**: beta de decenas de cuentas con 1–5 apartamentos; ~70 rutas, ~20 servicios, ~20 herramientas del agente, 33 tablas.

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ spec con 3 decisiones del host; plan, research, data-model, contratos y quickstart; ADR `docs/adr/0007-multitenancy.md` |
| II. Provider-agnostic | ✅ el adaptador de canal no sabe de cuentas (recibe credencial e ids); correo tras puerto `EmailSender`; Google tras un servicio `oauth_google` aislado |
| III. Human-in-the-loop | ✅ sin cambios en el flujo de confirmación; la confirmación queda ligada a la cuenta y al usuario (auditoría con `user_id`); una escritura pendiente no se ejecuta si la sesión se cierra o la cuenta se desactiva |
| IV. Tipado y pruebas | ✅ pruebas de aislamiento por cada tipo de dato, de falla cerrado, de acceso y de Google con transporte falso |
| V. Simplicidad (YAGNI) | ✅ una base compartida, sin infraestructura por cliente; una dependencia Python; un usuario por cuenta (membresía preparada, sin pantallas de invitación de usuarios) |
| VI. Aislamiento por cuenta | ✅ cuenta derivada solo de la sesión/clave del webhook/recorrido del cron; filtro automático + falla cerrado; secretos separados; datos públicos (eventos, mercado) sin datos privados |

**Post-diseño (re-check)**: ✅ sin violaciones. Riesgo vigilado: el bypass de plataforma (`session.info["platform"]`) se limita a `admin_service` y al recorrido del cron, con prueba que falla si se usa en otro módulo.

## Project Structure

### Documentation (this feature)

```text
specs/026-multitenant-accounts/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/accounts-api.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
apps/api/
├── app/models/account.py                 # Account, AccountOwned (mixin), PlatformSetting          [PR1/PR3]
├── app/models/auth.py                    # AppUser, Membership, UserSession, AuthToken, AuthAttempt, InviteCode [PR2/PR3]
├── app/models/*.py                       # AccountOwned en las 28 tablas del anfitrión; Event.city; uniques
├── app/db/tenancy.py                     # eventos ORM (filtro, before_flush, falla cerrado), tenant_session(), platform_session()
├── app/db/session.py                     # get_session sin contexto; el contexto lo pone require_ctx
├── app/core/context.py                   # RequestContext, require_ctx, require_platform_admin, AUTH_MODE legacy|sessions
├── app/auth/{passwords,tokens,ratelimit}.py
├── app/email/{base,resend,fake,templates}.py   # puerto EmailSender + Resend + plantillas es/en/pt
├── app/services/{auth_service,invite_service,admin_service,google_auth_service,account_service}.py
├── app/services/secret_service.py        # ámbito plataforma/cuenta, caché (account_id, name)
├── app/channels/factory.py               # get_adapter(session) por cuenta (sale de routes/sync.py)
├── app/services/{webhook,push,sync,intelligence,event,suggestion_engine,price_extension,channel_pricing,native_deal,pricing_app}_service.py  # singletons → por cuenta, ciudad
├── app/market/extractor.py · tavily_market.py   # ciudad como parámetro
├── app/agent/{orchestrator,prompts,tools}.py    # contexto de la cuenta, ciudad/moneda, ensure_unit
├── app/api/routes/{auth,admin,units,account}.py # NUEVAS
├── app/api/router.py                     # require_ctx en todos los routers salvo health/auth/hooks
├── migrations/versions/{f9a0b1c2d3e4_accounts,a1b2c3d4e5f7_auth,b2c3d4e5f6a8_invites}.py
├── scripts/scan_daily.py                 # recorre cuentas; eventos/mercado una vez por ciudad
└── tests/conftest.py + test_tenancy.py, test_isolation_*.py, test_auth.py, test_invites_admin.py, test_google_auth.py, test_scan_multi.py

apps/web/
├── middleware.ts                         # cookie sl_session (forma), rutas públicas nuevas
├── lib/session.ts                        # nombres/duraciones; ya no firma con APP_PASSWORD
├── app/api/proxy/[...path]/route.ts      # Bearer desde cookie, bloquea auth/*, borra cookie en 401
├── app/api/auth/**/route.ts              # login, register, logout(-all), verify, forgot, reset, claim, google/start|callback, handoff
├── app/(auth)/{login,register,forgot,reset,verify,claim}/page.tsx
├── app/(app)/admin/page.tsx              # invitaciones, cuentas, registro abierto, secretos de plataforma, modelo IA
├── app/(app)/settings/page.tsx           # secretos de la cuenta; "Mi cuenta" (nombre, cerrar todas las sesiones)
├── lib/active-unit.ts · components/empty-state.tsx   # unidad desde GET /units; estado vacío sin conexión
├── lib/api.ts                            # 401 → /login
├── lib/i18n/catalog/{auth,admin}.ts      # es/en/pt
└── components/native/native-bridge.tsx   # Google en la app (Browser + appUrlOpen) [PR4]

apps/mobile/ (PR4)
├── package.json                          # @capacitor/browser
└── android/app/src/main/AndroidManifest.xml   # intent-filter com.staylever.app://auth

docs/accounts.md                          # guía del host: reclamar, Resend, Google, invitar, administrar
docs/adr/0007-multitenancy.md
```

**Structure Decision**: se mantiene el monorepo; la multitenencia vive en la capa de datos (`app/db/tenancy.py`) y en el contexto de la petición (`app/core/context.py`), de modo que los servicios existentes casi no cambian salvo los singletons y los puntos con Medellín/COP fijos.

## Decisiones clave (detalle en research.md)

1. **Filtro automático por cuenta + falla cerrado** (D1) en lugar de filtrar a mano ~90 consultas.
2. **Sesiones opacas en la API** (D2), Argon2id (D3), límite de intentos persistente (D4).
3. **Resend** tras `EmailSender` (D5); **Google** con PKCE y estado en servidor; en Android, navegador del sistema + esquema `com.staylever.app://auth` + verificador (D7).
4. **Reclamación** de la cuenta nº 1 con la contraseña actual, una sola vez (D9).
5. **Secretos** de plataforma vs. cuenta (D10); **channel manager por cuenta** y propiedad única entre cuentas (D11).
6. **Cron por cuenta** con fallos aislados; **eventos y mercado por ciudad**, compartidos (D12).
7. **4 PRs desplegables** (D13): PR1 sin cambio visible (`AUTH_MODE=legacy` → cuenta nº 1), PR2 activa sesiones.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Una consulta escapa al filtro | falla cerrado en pruebas + prueba que recorre todas las rutas con dos cuentas (SC-003) |
| Migración larga o parcial en producción | respaldo previo; pasos idempotentes; prueba sobre copia con conteos (quickstart) |
| El host queda fuera tras PR2 | reclamación con la contraseña actual; sin verificación de correo obligatoria para la reclamación; documentación paso a paso |
| Correo o Google sin configurar | registro por correo devuelve 503 claro; Google oculto si no hay credenciales; el host puede operar con la reclamación e invitaciones |
| App 1.0.0 sin soporte de Google | la web oculta el botón y pide actualizar; el login por correo funciona sin reinstalar |
| Costos de IA con más cuentas | eventos/mercado por ciudad una vez; límites por cuenta en #144 |

## Complexity Tracking

Sin violaciones.
