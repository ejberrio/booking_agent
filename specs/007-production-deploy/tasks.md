---
description: "Task list — Despliegue en producción (Railway + Neon)"
---

# Tasks: Despliegue en producción (Railway + Neon)

**Input**: Design documents from `/specs/007-production-deploy/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Se incluyen SOLO los tests en límites que exige la Constitución IV (normalización SSL de la DB y `/health` con verificación de DB), por ser puntos que pueden tumbar producción.

**Organization**: Tareas agrupadas por historia de usuario (US1=P1 acceso público seguro, US2=P1 deploy reproducible/CD, US3=P2 verificación de salud).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede correr en paralelo (archivos distintos, sin dependencias)
- Rutas exactas en cada tarea. Monorepo: `apps/api/`, `apps/web/`, `docs/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Andamiaje de despliegue compartido y registro de decisiones.

- [X] T001 Crear ADR de la decisión de despliegue en `docs/adr/0002-deploy-railway-neon.md` (web pública + API privada con proxy, Neon, CD; Constitución I)
- [X] T002 [P] Crear `apps/api/.dockerignore` (excluir `.venv`, `__pycache__`, `tests`, caches)
- [X] T003 [P] Crear `apps/web/.dockerignore` (excluir `node_modules`, `.next`, `.git`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Plumbing que TODAS las historias necesitan: conexión SSL a Neon, imágenes de contenedor y arranque con migraciones. Sin esto nada despliega.

**⚠️ CRITICAL**: Ninguna historia puede completarse hasta terminar esta fase.

- [X] T004 Implementar helper de normalización de `DATABASE_URL` (forzar driver `postgresql+asyncpg`, quitar `sslmode`/`channel_binding`, derivar SSL) en `apps/api/app/core/config.py`
- [X] T005 [P] Test de normalización SSL en `apps/api/tests/test_db_url_ssl.py` (URL con `sslmode=require` → sin el parámetro + `connect_args` con SSL)
- [X] T006 Aplicar el helper en el engine de la app: `create_async_engine(..., connect_args=ssl, pool_pre_ping=True)` en `apps/api/app/db/session.py` (pool_pre_ping cubre el autosuspend de Neon)
- [X] T007 Aplicar el mismo helper de normalización/SSL en `apps/api/migrations/env.py` (que las migraciones conecten a Neon con SSL)
- [X] T008 [P] Crear `apps/api/scripts/start.sh` → `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port "$PORT"` (idempotente)
- [X] T009 Crear `apps/api/Dockerfile` (base Python acorde a `requires-python`, `uv sync --frozen --no-dev`, copia app, `CMD ["sh","scripts/start.sh"]`)
- [X] T010 Activar `output: 'standalone'` en `apps/web/next.config.ts`
- [X] T011 [P] Crear `apps/web/Dockerfile` (multi-stage: deps→build→runtime node-alpine; runtime copia `.next/standalone`+`.next/static`+`public`; `CMD ["node","server.js"]`, `HOSTNAME=0.0.0.0`, escucha `$PORT`)

**Checkpoint**: Imágenes construyen localmente; la app conecta a Postgres con SSL; `alembic upgrade head` corre al arrancar.

---

## Phase 3: User Story 1 - Acceso público y seguro (Priority: P1) 🎯 MVP

**Goal**: Web como único servicio público que proxya server-side a la API privada; el navegador nunca toca la API; el login existente protege también la API; sin CORS.

**Independent Test**: Con la API corriendo como "interna" (local), levantar la web, iniciar sesión y confirmar que calendario/chat cargan datos vía `/api/proxy` (no vía `NEXT_PUBLIC_API_URL`), y que sin sesión se redirige a login.

- [X] T012 [US1] Crear el route handler de proxy en `apps/web/app/api/proxy/[...path]/route.ts` (GET/POST/PUT/PATCH/DELETE; preserva método, query, headers relevantes y body; propaga status/cuerpo; reenvía `ReadableStream` para SSE; lee `API_INTERNAL_URL` solo en servidor; 502 genérico si la API no responde)
- [X] T013 [US1] Cambiar la base de `apps/web/lib/api.ts` de `process.env.NEXT_PUBLIC_API_URL` a la ruta relativa `"/api/proxy"`
- [X] T014 [US1] Ajustar el cliente SSE del chat en `apps/web/lib/sse.ts` para usar `"/api/proxy/chat/stream"` (streaming a través del proxy)
- [X] T015 [US1] Verificar que `apps/web/middleware.ts` cubre `/api/proxy/*` (no está en la lista pública) y que `/api/login`/`/login` siguen abiertos
- [X] T016 [US1] `npm run build` verde en `apps/web` (modo standalone) y confirmar que no queda referencia a `NEXT_PUBLIC_API_URL` en el bundle

**Checkpoint**: La web sirve y proxya a la API; el acceso exige login; la API no se invoca desde el navegador.

---

## Phase 4: User Story 2 - Deploy reproducible + CD (Priority: P1)

**Goal**: Publicar de forma reproducible con artefactos versionados, migraciones automáticas al arrancar, despliegue continuo al push a `main`, y guía del operador.

**Independent Test**: Siguiendo `docs/deploy.md`, un operador lleva la app de cero a una URL pública; un push a `main` dispara un redeploy que aplica migraciones sin pasos manuales.

- [X] T017 [US2] Verificar que `apps/api/scripts/start.sh` aplica migraciones idempotentes y arranca uvicorn (validación end-to-end del arranque)
- [X] T018 [US2] Actualizar `.env.example` (raíz) con las variables de producción y referencia a `specs/007-production-deploy/contracts/environment.md` (incluye `API_INTERNAL_URL`, `ENVIRONMENT=production`; sin `NEXT_PUBLIC_API_URL`)
- [X] T019 [US2] Escribir la guía del operador en `docs/deploy.md` (Neon; Railway 3 servicios web/api/scan con Root Directory y dominios; variables; CD por push a `main`; primer deploy)
- [X] T020 [P] [US2] Añadir configuración declarativa por servicio si aplica (`apps/api/railway.json` / `apps/web/railway.json`: builder Dockerfile, healthcheckPath `/health`, restartPolicy) o documentar el equivalente en el dashboard en `docs/deploy.md`

**Checkpoint**: La guía permite desplegar de cero; los cambios en `main` se publican solos con migraciones aplicadas.

---

## Phase 5: User Story 3 - Verificación de salud + cron (Priority: P2)

**Goal**: `/health` que verifica la DB, escaneo de mercado diario por cron, y checklist de verificación post-deploy.

**Independent Test**: Llamar `/health` con DB arriba (200/`healthy`) y simular DB caída (503/`degraded`); confirmar que el cron ejecuta `scan_daily` y registra una corrida; recorrer el checklist post-deploy en verde.

- [X] T021 [US3] Ampliar `apps/api/app/api/routes/health.py`: `GET /health` ejecuta `SELECT 1`; responde `{"status":"healthy","db":"up"}` (200) o `{"status":"degraded","db":"down"}` (503); sin exponer secretos
- [X] T022 [P] [US3] Test de salud en `apps/api/tests/test_health.py` (DB OK → 200/healthy; sesión que falla → 503/degraded)
- [X] T023 [US3] Documentar el servicio cron `scan` en `docs/deploy.md` (reutiliza imagen de `api`, `Cron Schedule` `0 13 * * *`, comando `python -m scripts.scan_daily`, mismas variables; nota Constitución III: solo propone sugerencias)
- [X] T024 [US3] Añadir el checklist de verificación post-deploy a `docs/deploy.md` (health verde, migraciones aplicadas, login, `/sync/test` vía proxy, `/sync/import`, corrida del cron)

**Checkpoint**: Salud observable (incluida la DB); escaneo diario automático; verificación reproducible.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cierre de calidad y seguridad.

- [X] T025 [P] Actualizar `docs/deploy.md`/`README.md` con notas finales y enlazar el ADR
- [X] T026 Ejecutar `uv run ruff check .` + `uv run pytest` (api) y `npm run build` (web) — todo verde
- [X] T027 Revisión de seguridad: `git grep` de secretos (no hay claves en el repo); confirmar API sin dominio público y proxy server-only; CORS innecesario
- [X] T028 Dry-run de la guía `docs/deploy.md` (revisión de pasos y variables contra `contracts/environment.md`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; **bloquea** todas las historias.
- **US1 (Phase 3)**: depende de Foundational (necesita Dockerfile web/standalone y la API construible).
- **US2 (Phase 4)**: depende de Foundational (Dockerfile api + start.sh); puede ir en paralelo a US1.
- **US3 (Phase 5)**: depende de Foundational; el cron depende de la imagen de `api` (T009).
- **Polish (Phase 6)**: tras completar las historias deseadas.

### User Story Dependencies

- **US1 (P1)**: independiente; entrega el acceso seguro (proxy).
- **US2 (P1)**: independiente; entrega la reproducibilidad/CD. (US1 y US2 juntas = deploy realmente usable.)
- **US3 (P2)**: independiente; añade observabilidad y automatización. No bloquea a US1/US2.

### Within Each Story

- En Foundational: T004 (helper) antes de T006/T007 (uso del helper). T005 (test SSL) tras T004.
- En US1: T012 (proxy) antes de T013/T014 (clientes que lo consumen); T016 (build) al final.
- En US3: T021 (health) antes de T022 (su test).

---

## Parallel Opportunities

- Setup: T002 y T003 en paralelo.
- Foundational: T005 ‖ T008 ‖ T011 (archivos distintos) tras tener T004; T009/T010 según sus archivos.
- Una vez Foundational completo, **US1 y US2 pueden avanzar en paralelo** (web vs api/docs).
- US3: T022 en paralelo con tareas de documentación.

---

## Implementation Strategy

### MVP (deploy usable)

1. Phase 1 (Setup) → Phase 2 (Foundational).
2. Phase 3 (US1) + Phase 4 (US2) → **la app queda en línea, pública y segura, con CD**.
3. STOP y validar: desplegar siguiendo `docs/deploy.md`, iniciar sesión, ver datos reales, push de prueba a `main`.

### Incremental

4. Phase 5 (US3): health+DB, cron diario, checklist → observabilidad y frescura.
5. Phase 6 (Polish): seguridad, tests verdes, dry-run de la guía.

---

## Notes

- `[P]` = archivos distintos, sin dependencias.
- Secretos solo por variables de Railway; nunca en el repo ni en logs (verificado en T027).
- Tests mínimos por Constitución IV: SSL de DB (T005) y health con DB (T022).
- La creación de cuentas Railway/Neon, la facturación y pulsar "deploy" las hace el operador (humano), no estas tareas.
- Commit por tarea o grupo lógico; mantener CI verde.
