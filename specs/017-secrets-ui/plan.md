# Implementation Plan: Gestión de secretos (API keys) desde la interfaz

**Branch**: `017-secrets-ui` | **Date**: 2026-07-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-secrets-ui/spec.md`

## Summary

Servicio nuevo `secret_service` con caché en memoria del proceso: `get_secret(name)` SÍNCRONO que resuelve BD-cifrada > variable de entorno (la caché se carga en el lifespan de la API y se actualiza write-through al guardar/quitar — rotación inmediata sin redeploy; el scan la carga al inicio de su corrida). Cifrado **Fernet** (`cryptography`, dependencia nueva) con clave derivada de `SECRET_KEY` (SHA-256 → base64); `InvalidToken` ⇒ estado "ilegible" + fallback honesto. Los 3 consumidores cambian a `get_secret`: LLM (pasa `api_key=` por llamada a LiteLLM según proveedor — hoy depende del entorno del proceso), Tavily y `get_adapter` de Beds24. Endpoints write-only `/settings/secrets` (estado enmascarado, PUT/DELETE, test por servicio) + tarjeta en Configuración. Tablas nuevas `secret_entry` y `secret_change_log` (auditoría sin valores).

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (web)
**Primary Dependencies**: FastAPI + SQLAlchemy async; **`cryptography>=43` (NUEVA — Fernet)**; LiteLLM (acepta `api_key` por llamada); react-query
**Storage**: PostgreSQL / SQLite tests. **UNA migración** (`e2f3a4b5c6d7`, down `d1e2f3a4b5c6`): `secret_entry` + `secret_change_log`.
**Testing**: pytest con dobles (cifrado real con SECRET_KEY de test; proveedores falsos para los tests de "probar"); web `npm run build`
**Target Platform**: Railway (API privada tras el proxy con login — única puerta)
**Project Type**: monorepo web application
**Performance Goals**: n/a (4 secretos; caché en memoria O(1))
**Constraints**: valores NUNCA en logs/respuestas/repo (Constitución: "Secretos cifrados en reposo; nunca credenciales en el repositorio ni en logs"); sin secretos en BD → comportamiento idéntico (210 tests verdes); el agente NO gana herramientas de secretos
**Scale/Scope**: single-tenant; lista cerrada de 4 secretos; ~8 archivos API + ~3 web + 1 migración

## Constitution Check

*Feature sensible: revisión con lupa (pedida por el issue #99).*

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo; **ADR 0005** (gestión de secretos: cifrado, precedencia, superficie) — sí amerita ADR por ser decisión de seguridad |
| II. Provider-agnostic | ✅ `get_secret(name)` es neutro; los nombres son de la config existente; nada de un proveedor se filtra al dominio |
| III. Human-in-the-loop (NO NEGOCIABLE) | ✅ no hay escrituras a canales: guardar un secreto es config local (equivale a editar Railway, que el host ya hace sin preview); "Probar" es solo lectura/ping. El riesgo real (rotar el token de Beds24 por uno malo) queda mitigado por el botón Probar + auditoría + fallback |
| IV. Tipado y pruebas | ✅ cifrado/descifrado, precedencia, fallback ilegible, enmascaramiento y no-filtración con tests dedicados (es la frontera que puede costar TODO el canal) |
| V. Simplicidad | ✅ caché de módulo + Fernet estándar; sin vault externo, sin rotación automática, sin multiusuario (YAGNI) |
| **Restricción técnica: "Secretos cifrados en reposo; nunca en repo ni logs"** | ✅ Fernet en BD; el middleware ya no loguea cuerpos; los handlers de error devuelven mensajes fijos sin interpolar valores; tests SC-002 con valor centinela |

**Post-diseño (re-check)**: ✅ sin violaciones. Superficie de exposición revisada: GET nunca devuelve valores (ni cifrados); PUT no eco-a el valor; auditoría solo pista; el test de servicio construye el cliente localmente y descarta el valor.

## Project Structure

### Documentation (this feature)

```text
specs/017-secrets-ui/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/secrets-api.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/api/
├── pyproject.toml                          # + cryptography>=43
├── app/models/secret.py                    # NUEVO: SecretEntry, SecretChangeLog
├── migrations/versions/e2f3a4b5c6d7_secret_entries.py
├── app/services/secret_service.py          # NUEVO: cifrado, caché, resolve, estado, auditoría
├── app/api/routes/secrets.py               # NUEVO: GET estado / PUT / DELETE / POST test
├── app/api/router.py                       # registrar (prefijo /settings/secrets)
├── app/main.py                             # lifespan: cargar caché (resiliente)
├── app/llm/client.py                       # api_key por llamada vía get_secret
├── app/search/tavily.py                    # api_key vía get_secret
├── app/api/routes/sync.py                  # get_adapter: refresh_token vía get_secret
├── scripts/scan_daily.py                   # cargar caché al inicio de la corrida
└── tests/test_secret_service.py + test_secrets_api.py

apps/web/
├── app/(app)/settings/page.tsx             # tarjeta "Secretos" (estado + write-only + probar)
└── lib/{types,api}.ts                      # SecretStatus + funciones

docs/adr/0005-secrets-management.md · docs/operations.md
```

**Structure Decision**: monorepo existente; el módulo con lógica nueva es `secret_service`.

## Decisiones clave (detalle en research.md)

1. **Fernet con clave derivada de SECRET_KEY** — `base64url(SHA256(secret_key))`; autenticado (detecta corrupción/clave rotada vía `InvalidToken` → estado "ilegible" + fallback env; nunca rompe arranque).
2. **Caché en memoria write-through** — `get_secret(name)` sync (los consumidores incluyen funciones sync como `get_adapter`); carga en lifespan de la API y al inicio del scan; escrituras actualizan BD y caché en la misma operación → rotación inmediata en la API, siguiente corrida en el scan.
3. **LiteLLM con `api_key` por llamada** — hoy LiteLLM lee el entorno del proceso (por eso una rotación en BD no le llegaría); `LiteLLMClient.chat` pasa `api_key=get_secret(provider_key)` resuelto por el prefijo del modelo/proveedor. `_has_key()` pasa a consultar `get_secret`.
4. **Lista cerrada** — `openai_api_key`, `anthropic_api_key`, `search_api_key`, `beds24_refresh_token`; cada una declara su servicio de prueba y qué funcionalidad apaga si falta.
5. **Probar por servicio** — LLM: completion mínima (`max_tokens=1`) con el modelo general configurado; búsqueda: 1 consulta mínima; Beds24: `test_connection()` con adaptador fresco. Errores → mensaje corto categorizado (credencial rechazada / servicio no disponible), sin interpolar el valor.
6. **Sin re-confirmación de contraseña** — decisión documentada en la spec (write-only + misma contraseña de sesión no cambia el modelo de amenaza).

## Fase 0 → research.md · Fase 1 → data-model.md, contracts/, quickstart.md

Incógnitas resueltas leyendo el código: consumidores exactos (llm/client, search/tavily, routes/sync.get_adapter), LiteLLM depende del entorno (motivo de la decisión 3), no hay lifespan actual en main.py (se añade), `cryptography` no estaba en las dependencias.
