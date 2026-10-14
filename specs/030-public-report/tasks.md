# Tasks: Página pública e informe gratis (030)

## Phase 1: Setup / Foundational
- [ ] T001 Generar `apps/api/app/data/municipios_co.json` (DIVIPOLA) y `apps/api/app/domain/municipalities.py` (búsqueda sin tildes, etiqueta "Municipio, Departamento", área metropolitana → ciudad principal)
- [ ] T002 Modelos `apps/api/app/models/public.py` (CityScan, PublicReport, WaitlistEntry, PublicMetric, PublicQuota) + `account.signup_source` + migración `f6a7b8c9d0e2_public_report.py`

## Phase 2: US1 Informe gratis (P1)
- [ ] T003 [US1] `apps/api/app/services/public_service.py`: límite por visitante, caché por ciudad + presupuesto diario, búsqueda con `extract_events`, cálculo con `suggest_price_v2`, top 3, token, métricas
- [ ] T004 [US1] Rutas `apps/api/app/api/routes/public.py` (/public/municipalities, /public/report, /public/visit) y registro en router; `scan_daily` registra `city_scan`
- [ ] T005 [US1] Web: `app/api/public/[...path]/route.ts` (x-client-ip), middleware (`/` sin sesión → /welcome, /api/public/ público), formulario e informe en `components/site/free-report.tsx`

## Phase 3: US2 Cuenta desde el informe (P1)
- [ ] T006 [US2] Cupo: `invite_service.registration_state` {enabled, quota, used, full}; registro abierto con cupo en `auth_service.register` y Google; `signup_source`; `report` token vincula el informe
- [ ] T007 [US2] Correo del informe completo al verificar (o con Google) una vez; plantilla en `auth/email/templates.py`
- [ ] T008 [US2] `GET /report/mine`; web `/report` (informe completo) y prellenado de `setup/manual`; register con `?report=` y lista de espera si está lleno
- [ ] T009 [US2] `POST /public/waitlist` (consentimiento, límites)

## Phase 4: US3 Landing (P2)
- [ ] T010 [US3] `/welcome` nueva: qué hace, para quién, capturas/ilustraciones, informe, FAQ, beta, legal; i18n `public.ts` es/en/pt; claro/oscuro; móvil

## Phase 5: US4 Admin (P2)
- [ ] T011 [US4] `/admin/beta` GET/PATCH, invitar/borrar de la lista de espera (correo con enlace); sección "Beta pública" en Administración

## Phase 6: Polish
- [ ] T012 Tests `apps/api/tests/test_public_report.py` (caché, presupuesto, límites, cálculo, cupo, lista de espera, vínculo, aislamiento) + suite completa + ruff/tsc/eslint/build
- [ ] T013 Privacidad (es/en/pt): informe público, lista de espera, métricas agregadas; `docs/` inventario de datos
