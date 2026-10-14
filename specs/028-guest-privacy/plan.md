# Implementation Plan: Privacidad de huéspedes y política de datos (Ley 1581)

**Branch**: `028-guest-privacy` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/028-guest-privacy/spec.md`

## Summary

Cuatro piezas sobre la base multicliente de la feature 026:

1. **Aceptación versionada** de Términos y Privacidad: tabla `terms_acceptance`, constante `LEGAL_VERSION`, casilla obligatoria en registro/Google/reclamación, y una **puerta en el servidor** (`require_ctx` responde `403 terms_required` salvo en una lista corta de rutas) más una pantalla de aceptación en la web/app.
2. **Nombre del huésped con vida limitada**: limpieza diaria por cuenta en el cron (`guest_name = NULL` si la salida fue hace > 365 días) y no guardarlo al importar reservas viejas.
3. **Derecho de acceso**: `GET /account/export` arma un JSON con todas las tablas de la cuenta (filtro automático), sin secretos.
4. **Derecho de supresión**: `POST /account/delete` con nombre de la cuenta + contraseña (o código por correo de 15 min); borra todas las filas de la cuenta en orden de dependencias, el usuario y sus sesiones; la cuenta queda como lápida (`status=deleted`, nombre vacío) para el registro del administrador y las invitaciones.

Más contenido: `/terms` nuevo y `/privacy` actualizado (es/en/pt), inventario interno `docs/data-inventory.md`.

## Technical Context

**Language/Version**: Python 3.12 (API FastAPI), TypeScript (Next.js 15)
**Primary Dependencies**: existentes (SQLAlchemy 2 async, Alembic, Resend vía `EmailSender`). Ninguna nueva.
**Storage**: PostgreSQL (Neon); 1 tabla nueva (`terms_acceptance`), 1 valor nuevo del enum `accountstatus` (`deleted`).
**Testing**: pytest (SQLite en memoria) — `test_privacy.py`; web `tsc`/`eslint`/`build`.
**Target Platform**: Railway (api, web, scan), app Android (misma web; sin APK nuevo).
**Performance Goals**: exportación < 1 min para cuentas de 1–5 aptos (miles de filas); limpieza diaria O(reservas viejas).
**Constraints**: principio VI; el administrador nunca ve nombres de huéspedes; no perder reservas del host; staging primero + copia de Neon.
**Scale/Scope**: decenas de cuentas; ~30 tablas por cuenta.

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ spec con decisiones del host; plan, research, data-model, contrato y quickstart |
| II. Provider-agnostic | ✅ el canal sigue entregando el nombre; la retención se aplica en el servicio de sincronización, no en el adaptador |
| III. Human-in-the-loop | ✅ sin cambios en escrituras al canal; el borrado de cuenta exige confirmación fuerte (nombre + identidad) |
| IV. Tipado y pruebas | ✅ pruebas de puerta de términos, retención, exportación sin secretos ni datos ajenos, y borrado completo sobre todas las tablas `AccountOwned` |
| V. Simplicidad | ✅ sin dependencias; versión como constante en el código; lápida en `account` en vez de tabla de registro |
| VI. Aislamiento por cuenta | ✅ exportación con el filtro automático; borrado con `account_id` explícito en el único módulo de plataforma autorizado (`privacy_service.py`, se agrega a la lista de `test_tenancy`) |

**Post-diseño**: ✅ sin violaciones. Riesgo vigilado: el borrado recorre tablas con un bypass de plataforma; la prueba verifica que no queda ninguna fila de la cuenta borrada y que las de otra cuenta siguen intactas.

## Project Structure

### Documentation (this feature)

```text
specs/028-guest-privacy/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/privacy-api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
apps/api/
├── app/core/legal.py                     # LEGAL_VERSION, GUEST_NAME_RETENTION_DAYS
├── app/models/auth.py                    # + TermsAcceptance
├── app/models/account.py                 # + AccountStatus.deleted
├── app/core/context.py                   # puerta terms_required en require_ctx
├── app/services/auth_service.py          # aceptar en registro/claim; me() con terms_required
├── app/services/google_auth_service.py   # aceptación en el estado de Google
├── app/services/privacy_service.py       # limpieza, exportación, borrado (bypass de plataforma)
├── app/services/sync_service.py          # no guardar nombre de reservas viejas
├── app/api/routes/auth.py                # POST /auth/terms/accept
├── app/api/routes/account.py             # GET /account/export, POST /account/delete(-code)
├── app/api/routes/admin.py               # cuentas eliminadas en el listado
├── app/email/templates.py                # código de borrado + confirmación
├── scripts/scan_daily.py                 # limpieza diaria por cuenta
├── migrations/versions/c3d4e5f6a7b9_privacy.py
└── tests/test_privacy.py

apps/web/
├── app/terms/page.tsx                    # Términos (público)
├── lib/i18n/catalog/site.ts              # + terms, privacy actualizada
├── lib/i18n/catalog/privacy.ts           # textos de la puerta, exportar y borrar
├── components/legal/terms-gate.tsx       # pantalla de aceptación en (app)
├── components/account/data-card.tsx      # Ajustes: descargar copia y borrar cuenta
├── components/auth/accept-terms.tsx      # casilla reutilizable
├── app/register/page.tsx, app/claim/page.tsx, components/auth/google-button.tsx
├── app/api/auth/{register,claim,terms}/route.ts, app/api/account/export/route.ts
└── middleware.ts                         # /terms público

docs/data-inventory.md                     # inventario interno de datos
docs/accounts.md                           # aceptar, exportar, borrar
```

**Structure Decision**: misma estructura del monorepo; un servicio nuevo (`privacy_service`) concentra todo lo que cruza tablas.

## Delivery

Un solo PR (feature acotada) → staging (el host prueba aceptación, exportación y borrado de la cuenta de prueba #2) → copia de Neon → producción.

## Complexity Tracking

Sin violaciones que justificar.
