# Tasks: Privacidad de huéspedes y política de datos (Feature 028)

**Input**: `specs/028-guest-privacy/` (spec, plan, research, data-model, contracts, quickstart)

## Phase 1: Setup

- [X] T001 `apps/api/app/core/legal.py`: `LEGAL_VERSION`, `GUEST_NAME_RETENTION_DAYS = 365`, rutas permitidas sin aceptación

## Phase 2: Foundational

- [X] T002 Modelo `TermsAcceptance` en `apps/api/app/models/auth.py` y `AccountStatus.deleted` en `apps/api/app/models/account.py`
- [X] T003 Migración `apps/api/migrations/versions/c3d4e5f6a7b9_privacy.py` (tabla + valor del enum; downgrade) y prueba upgrade/downgrade/check en PG local

## Phase 3: US1 Aceptar Términos y Privacidad (P1)

- [X] T004 [US1] `auth_service`: `has_accepted`, `accept_terms`; `register`/`claim` exigen `accept_terms`; `me()` con `terms_required` y `legal_version`
- [X] T005 [US1] `google_auth_service`: `accept_terms` en el estado; registrar aceptación al crear o vincular si vino marcada
- [X] T006 [US1] Puerta en `apps/api/app/core/context.py` (`403 terms_required`) + `POST /auth/terms/accept` en `routes/auth.py`
- [X] T007 [US1] Web: casilla `components/auth/accept-terms.tsx` en registro, reclamación y botón de Google; `components/legal/terms-gate.tsx` en `(app)/layout.tsx`; aceptación vía el proxy (`/auth/terms/accept`); manejo de `403 terms_required` en `lib/api.ts`
- [X] T008 [US1] Web: página pública `app/terms/page.tsx` y textos en `lib/i18n/catalog/site.ts` (es/en/pt); `/terms` en `middleware.ts`; enlaces en pie, entrada y registro

## Phase 4: US2 Nombre del huésped con vida limitada (P1)

- [X] T009 [US2] `privacy_service.purge_guest_names(session, today)`; llamada por cuenta en `scripts/scan_daily.py` con fallos aislados
- [X] T010 [US2] `sync_service`: no guardar `guest_name` si la salida fue hace más de 365 días

## Phase 5: US3 Descargar copia (P2)

- [X] T011 [US3] `privacy_service.export_account(session, ctx)` + `GET /account/export`; botón (vía el proxy) en `components/account/data-card.tsx`

## Phase 6: US4 Borrar cuenta (P2)

- [X] T012 [US4] `privacy_service.delete_account(account_id)` (bypass de plataforma; agregar a la lista de `test_tenancy`), `POST /account/delete-code`, `POST /account/delete`; plantillas de correo; admin muestra cuentas eliminadas
- [X] T013 [US4] Web: borrar cuenta en `data-card.tsx` (nombre + contraseña o código) y cierre de sesión

## Phase 7: US5 Documentos

- [X] T014 [US5] `/privacy` actualizada (retención, Encargado, derechos desde Ajustes, copias de 7 días) en es/en/pt
- [X] T015 [P] [US5] `docs/data-inventory.md` y `docs/accounts.md`

## Phase 8: Tests & Polish

- [X] T016 `apps/api/tests/test_privacy.py`: casilla obligatoria, puerta 403 y rutas permitidas, nueva versión vuelve a pedir, retención 13/11 meses e importación vieja, exportación sin secretos ni datos ajenos, borrado completo (todas las tablas `AccountOwned`) sin tocar otra cuenta, cuenta 1 protegida, código de borrado vencido/reusado, admin sin nombres de huéspedes
- [X] T017 Ajustar pruebas existentes (aceptación en registro/claim de los tests de 026)
- [ ] T018 ruff, pytest, tsc, eslint, build; staging; verificación del host; copia de Neon; producción; cerrar #145

## Dependencies

T001 → T002 → T003 → (US1 T004–T008) → US2/US3/US4 en paralelo → US5 → T016–T018.
