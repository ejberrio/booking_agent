# Implementation Plan: Página pública e informe gratis

**Branch**: `030-public-report` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

## Summary

Página de inicio pública en `/welcome` (a la que se redirige `/` sin sesión) con el **informe gratis**: el visitante elige un municipio de la lista oficial (DIVIPOLA, ~1.120), escribe su precio y recibe los 3 eventos más importantes de 6 meses con el precio sugerido por `suggest_price_v2` (mismo cálculo de la app). Los eventos se reutilizan de la tabla pública `event` si el municipio se escaneó hace < 7 días (`city_scan`); si no, se buscan una vez con el mismo extractor del escaneo diario (búsqueda + IA) dentro de un **presupuesto diario global**. Límite por visitante con hash HMAC diario de la IP (sin guardar la IP). **Registro abierto con cupo** sobre el ajuste existente `registration_open` (`{enabled, quota}`) y la columna `account.signup_source`; lleno el cupo → **lista de espera** con consentimiento. El informe se **vincula a la cuenta** al registrarse (token), prellena "Usar sin conexión", se ve completo en la app (`/report`) y se envía por correo una vez tras verificar el correo. **Métricas diarias agregadas** sin cookies, visibles en Administración junto al cupo, el presupuesto y la lista de espera.

## Technical Context

Python 3.12 / FastAPI / SQLAlchemy async / Alembic; Next.js 15. Sin dependencias nuevas. Municipios en `apps/api/app/data/municipios_co.json` (código DANE, municipio, departamento) generado una vez desde datos.gov.co (DIVIPOLA) y versionado. La web llama a la API privada desde el servidor (`/api/public/*` → `API_INTERNAL_URL/public/*`) pasando la IP del visitante en `x-client-ip`; el navegador nunca ve la API.

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ spec con decisiones del host, plan, contrato, tareas |
| II. Provider-agnostic | ✅ reutiliza los puertos `SearchProvider`/`LLM` y `extract_events`; nada atado a Tavily |
| III. Human-in-the-loop | ✅ el informe solo lee y calcula; no publica nada ni crea cuentas sin acción del visitante |
| IV. Pruebas | ✅ caché/presupuesto, límites, cálculo, cupo, lista de espera, vínculo informe→cuenta, aislamiento |
| V. Simplicidad | ✅ ajuste existente para el cupo, una tabla por concepto, contadores diarios en vez de analítica externa, sin captcha en v1 |
| VI. Aislamiento | ✅ el informe público solo lee `event` (datos públicos por ciudad); `public_report` solo se lee por su cuenta (`/report/mine` con contexto) o por el admin agregado; ninguna ruta pública toca tablas `AccountOwned` |

## Source Code

```text
apps/api/app/data/municipios_co.json         # DIVIPOLA (código, nombre, departamento)
apps/api/app/domain/municipalities.py        # carga, búsqueda, área metropolitana → ciudad principal
apps/api/app/models/public.py                # CityScan, PublicReport, Waitlist, PublicMetric, PublicQuota
apps/api/app/models/account.py               # signup_source (open | invite | admin)
apps/api/app/services/public_service.py      # informe, caché/presupuesto, límites, métricas, lista de espera
apps/api/app/services/invite_service.py      # cupo: registration_state() {enabled, quota, used, full}
apps/api/app/services/auth_service.py        # registro abierto con cupo + report token; correo del informe al verificar
apps/api/app/services/google_auth_service.py # idem para Google
apps/api/app/api/routes/public.py            # /public/municipalities, /public/report, /public/waitlist, /public/visit
apps/api/app/api/routes/report.py            # /report/mine (con contexto): informe completo + prellenado
apps/api/app/api/routes/admin.py             # /admin/beta (cupo, presupuesto, métricas, lista de espera, invitar)
apps/api/app/auth/email/templates.py         # full_report, waitlist_invite
apps/api/scripts/scan_daily.py               # registra city_scan de las ciudades escaneadas
apps/api/migrations/versions/f6a7b8c9d0e2_public_report.py
apps/api/tests/test_public_report.py
apps/web/middleware.ts                       # "/" sin sesión → /welcome; /api/public/ público
apps/web/app/api/public/[...path]/route.ts   # reenvío a la API con x-client-ip
apps/web/app/welcome/page.tsx                # landing nueva + formulario del informe
apps/web/components/site/*                   # secciones, informe, lista de espera
apps/web/app/register/page.tsx               # cupo lleno → lista de espera; ?report=token
apps/web/app/(app)/report/page.tsx           # informe completo en la app
apps/web/app/(app)/setup/manual/page.tsx     # prellenado desde el informe
apps/web/app/(app)/admin/...                 # sección "Beta pública"
apps/web/lib/i18n/catalog/public.ts          # es/en/pt
apps/web/app/privacy (catálogo legal)        # informe público, lista de espera, métricas agregadas
```

## Delivery

Un PR → staging (el host prueba como visitante en ventana privada: informe, registro con cupo, lista de espera, admin) → copia de Neon `antes-de-030` → producción (el registro abierto queda **apagado** hasta que el host lo encienda en Administración).
