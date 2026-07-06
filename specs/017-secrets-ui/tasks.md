# Tasks: Gestión de secretos (API keys) desde la interfaz

**Input**: Design documents from `/specs/017-secrets-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/secrets-api.md, quickstart.md

**Tests**: incluidos y con lupa (feature sensible: cifrado, no-exposición y precedencia pueden costar TODO el canal). Test centinela SC-002 obligatorio.

**Organization**: por user story. Setup = dependencia nueva; Foundational = modelo + migración + servicio de cifrado/caché (lo usan todas).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable · **[Story]**: US1 (rotar), US2 (estado), US3 (probar), US4 (auditoría)

## Path Conventions

Monorepo: `apps/api/` y `apps/web/`, según plan.md.

---

## Phase 1: Setup

- [X] T001 Añadir `cryptography>=43` a `apps/api/pyproject.toml` y `uv sync` (verificar que el lockfile se actualiza)

---

## Phase 2: Foundational (bloqueante)

- [X] T002 Crear `apps/api/app/models/secret.py`: `SecretEntry` (name String(60) UNIQUE, value_encrypted Text, hint String(8), TimestampMixin) y `SecretChangeLog` (name String(60), action String(12), hint String(8), changed_at DateTime tz); exportar en `apps/api/app/models/__init__.py`
- [X] T003 Migración `apps/api/migrations/versions/e2f3a4b5c6d7_secret_entries.py` (down_revision `d1e2f3a4b5c6`): ambas tablas, sin enums de BD; downgrade limpio
- [X] T004 Crear `apps/api/app/services/secret_service.py`: `SECRET_NAMES` (lista cerrada de 4 con label + service descriptivo), `SecretError`; Fernet con clave `urlsafe_b64encode(sha256(settings.secret_key))`; `_cache`/`_unreadable` de módulo; `load_cache(session)` (descifra todo; InvalidToken → unreadable, sin excepción); `get_secret(name)` SYNC (caché > settings); `set_secret(session, name, value)` (strip, no vacío, cifra, upsert, hint últimos 4 — vacío si len<8, write-through, audita "set"); `delete_secret` (borra, caché, audita "deleted"); `status(session)` (estado enmascarado por nombre incl. hint del env si source=env); `list_audit(session)`
- [X] T005 Tests en `apps/api/tests/test_secret_service.py` (con fixture autouse que limpia `_cache`/`_unreadable` entre tests — la caché es estado de módulo): round-trip cifrado; clave distinta → unreadable + fallback env + arranque sin excepción; precedencia BD>env>None; write-through inmediato; hint (normal, <8 chars); validación vacío; FR-012 (sin filas → get_secret == settings.*); auditoría set/deleted sin valores

**Checkpoint**: núcleo criptográfico y de resolución probado.

---

## Phase 3: User Story 1+2 — Rotar y ver estado (P1, mismo endpoint/UI)

**Goal**: endpoints write-only + tarjeta en Configuración; rotación inmediata en los consumidores.

**Independent Test**: PUT → estado source=app con pista y el consumidor usa el valor nuevo; DELETE → vuelve a env; GET nunca contiene valores (centinela).

- [X] T006 [US1] Crear `apps/api/app/api/routes/secrets.py`: `GET /settings/secrets` (estado), `PUT /{name}` (`{"value"}` → estado, 422 vacío, 404 nombre inválido), `DELETE /{name}` (404 si no hay guardado), `GET /audit`; registrar en `apps/api/app/api/router.py` (prefijo `/settings/secrets`); mensajes de error FIJOS sin interpolar valores
- [X] T007 [US1] Consumidores → `get_secret`: `apps/api/app/llm/client.py` (`_has_key()` y `LiteLLMClient.chat` pasa `api_key=` resuelto por proveedor — prefijo `anthropic/` → anthropic_api_key, si no openai_api_key; si get_secret devuelve None no pasar el kwarg — comportamiento actual); `apps/api/app/search/tavily.py` (`api_key or get_secret("search_api_key") or ""`); `apps/api/app/api/routes/sync.py` (`get_adapter`: `refresh_token=get_secret("beds24_refresh_token")`)
- [X] T008 [US1] Arranque: lifespan en `apps/api/app/main.py` que llama `secret_service.load_cache` en try/except (warning fijo sin valores si falla); `apps/api/scripts/scan_daily.py` llama al loader al inicio de la corrida
- [X] T009 [US1] Tests en `apps/api/tests/test_secrets_api.py` (cliente ASGITransport): PUT→GET estado correcto (source=app, hint); DELETE→env; 404/422; **centinela SC-002** ("SENTINEL-XYZ-1234" no aparece en NINGUNA respuesta de GET/PUT/DELETE/audit); rotación efectiva (tras PUT, get_secret devuelve el nuevo sin recargar)
- [X] T010 [P] [US2] Web: `SecretStatus` en `apps/web/lib/types.ts` + `listSecrets/setSecret/deleteSecret/testSecret/listSecretAudit` en `apps/web/lib/api.ts`
- [X] T011 [US2] Web: tarjeta "Secretos" en `apps/web/app/(app)/settings/page.tsx`: por secreto — label, servicio, estado (configurado · origen · pista · último cambio · "ilegible" si aplica), input type=password write-only + Guardar (limpia el campo al éxito), Quitar (solo source=app, confirmación simple), aviso fijo del scan; toasts con `detail`

**Checkpoint**: rotar desde la UI funciona de punta a punta.

---

## Phase 4: User Story 3 — Probar por servicio (P2)

**Goal**: `POST /settings/secrets/{name}/test` honesto, solo lectura, sin filtrar valores.

**Independent Test**: con dobles — credencial válida → ok; inválida → fallo categorizado; detail nunca contiene el valor.

- [X] T012 [US3] En `apps/api/app/api/routes/secrets.py` + `secret_service`: `POST /{name}/test` — llm (completion `max_tokens=1` con modelo general de LLMConfig o default y `api_key` resuelto), search (1 consulta `max_results=1`), beds24 (`test_connection()` de adaptador fresco, cerrándolo); respuesta `{ok, detail}` con detail categorizado FIJO ("conexión OK…", "credencial rechazada por el proveedor", "servicio no disponible"); excepciones crudas jamás en la respuesta
- [X] T013 [US3] Tests (en test_secrets_api.py): monkeypatch de los 3 probadores → ok/fallo; detail sin el valor centinela; el test de beds24 no escribe nada (solo test_connection)
- [X] T014 [US3] Web: botón "Probar" por secreto en la tarjeta (resultado inline éxito/fallo con el detail)

**Checkpoint**: rotar → probar → confiar.

---

## Phase 5: User Story 4 — Auditoría visible (P2)

- [X] T015 [US4] Web: sección "Últimos cambios" en la tarjeta de Secretos (GET /settings/secrets/audit → nombre, acción, pista, fecha; lista corta)

---

## Phase 6: Polish & Cross-Cutting

- [X] T016 [P] `docs/adr/0005-secrets-management.md` (decisiones: Fernet+derivación, caché write-through, precedencia, write-only, sin re-auth — con el porqué) y sección en `docs/operations.md` (rotar un secreto paso a paso; el scan la toma en su próxima corrida; SECRET_KEY rotado → "ilegible" + re-guardar)
- [X] T017 Verificación final: `uv run pytest -q` + ruff; `npm run build`; `alembic heads` único; grep del diff por posibles fugas (`value` en respuestas/logs); revisar FR-012
- [ ] T018 Verificación EN VIVO tras merge: GET estado (4 con source=env y pistas correctas contra Railway); EL HOST rota o re-guarda un valor desde la UI (el agente nunca los maneja) → estado source=app → Probar OK → servicio real funcionando → auditoría con pista; opcional reversible: Quitar → vuelve a env

---

## Dependencies & Execution Order

- T001 → T002-T005 (Foundational) → resto.
- US1+2 (T006-T011): T006-T008 secuenciales sobre archivos distintos pero lógicamente encadenados; T010 ∥ con T006; T011 tras T006+T010.
- US3 (T012-T014) tras T006; US4 (T015) tras T006.
- Polish al final; T018 tras merge (el host pega los valores).

```
T001 ─▶ T002-T005 ─▶ T006-T009 ─┬▶ T012-T014 (probar) ─┐
                    T010 ─▶ T011 ┴▶ T015 (auditoría UI) ─┼▶ T016-T017 ─▶ merge ─▶ T018 (host)
```

## Implementation Strategy

**MVP = Setup + Foundational + US1/US2** (rotar con estado enmascarado). Probar y auditoría-UI son el segundo incremento. Una rama/PR; commits por fase. La verificación en vivo la protagoniza el HOST (pega los valores; el agente jamás los ve — ni siquiera en el chat).
