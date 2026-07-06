# Research: Feature 017 — Gestión de secretos desde la interfaz

**Date**: 2026-07-04 · Método: lectura del código + documentación de `cryptography`/LiteLLM.

## R1. Mecanismo de cifrado (FR-002)

- **Decision**: **Fernet** (paquete `cryptography`, dependencia nueva) con clave derivada del `SECRET_KEY` existente: `key = urlsafe_b64encode(sha256(secret_key.encode()).digest())`.
- **Rationale**: Fernet = AES-128-CBC + HMAC (cifrado AUTENTICADO): un valor corrupto o cifrado con otra clave lanza `InvalidToken` de forma determinista → implementamos el estado "ilegible" + fallback (FR-006) sin heurísticas. Estándar, auditado, sin parámetros que elegir mal. La derivación por SHA-256 es suficiente aquí: el SECRET_KEY ya es material aleatorio de alta entropía (generado en el deploy), no una contraseña humana (no se necesita KDF lento tipo scrypt).
- **Alternatives considered**: AES-GCM manual (más control, más formas de equivocarse — rechazado); guardar en texto plano con permisos de BD (viola la constitución); vault externo (YAGNI single-tenant, dependencia de infraestructura nueva).

## R2. Cómo llega la rotación a los consumidores (FR-005)

- **Hallazgos**: (a) `get_adapter()` (sync) lee `settings.beds24_refresh_token` al construir el adaptador POR PETICIÓN → con resolver ahí, la rotación aplica en la siguiente petición; (b) `TavilyProvider.__init__` lee `settings.search_api_key` al construirse (por corrida de scan); (c) **LiteLLM lee la API key del ENTORNO del proceso** — una rotación guardada en BD jamás le llegaría si no se pasa explícita.
- **Decision**: caché en memoria de módulo (`_cache: dict[str, str | None]`) con `get_secret(name)` SÍNCRONO: `_cache` (BD, cargada en el lifespan de la API y al inicio del scan) > `settings.<name>` (entorno). Escrituras (PUT/DELETE) actualizan BD y caché write-through. Consumidores: `get_adapter` → `get_secret("beds24_refresh_token")`; `TavilyProvider` → `get_secret("search_api_key")`; `LiteLLMClient.chat` → `api_key=get_secret(...)` elegido por el proveedor del modelo (prefijo `anthropic/` → anthropic_api_key; si no → openai_api_key), y `_has_key()` consulta `get_secret`.
- **Rationale**: `get_secret` sync permite usarlo en `get_adapter` (sync) sin reestructurar; la caché es coherente porque la API es un solo proceso (uvicorn) y el único escritor es el endpoint; el scan es proceso aparte de corrida corta → cargar al inicio es suficiente (comunicado en UI/docs).
- **Alternatives considered**: consulta a BD en cada resolución (exige async en todos los consumidores; get_adapter es sync); escribir `os.environ` al rotar (funciona con LiteLLM pero es estado global invisible y no probado — rechazado por explícito > implícito).

## R3. Superficie de no-exposición (FR-003/FR-009, SC-002)

- **Decision**: (a) GET de estado devuelve `{name, configured, source: "app"|"env"|None, hint, updated_at, unreadable}` — jamás el valor ni el cifrado; (b) PUT responde el MISMO shape de estado (no eco del valor); (c) auditoría guarda solo `hint` (últimos 4; si el valor tiene <8 chars, hint vacío para no revelar proporciones); (d) mensajes de error FIJOS (nunca interpolan el valor ni la excepción del cifrado); (e) el middleware de logging existente ya registra solo method/path/status (verificado en 016); (f) test SC-002: guardar centinela `"SENTINEL-XYZ-1234"` y assert de que no aparece en ninguna respuesta de la API de secretos ni en la auditoría.
- **Rationale**: cada superficie enumerada y testeada; write-only real.

## R4. Botón "Probar" por servicio (FR-008)

- **Decision**: `POST /settings/secrets/{name}/test` — por nombre: `openai_api_key`/`anthropic_api_key` → completion mínima (`max_tokens=1`, modelo general de LLMConfig o default) con `api_key` resuelto; `search_api_key` → 1 búsqueda `max_results=1`; `beds24_refresh_token` → `test_connection()` de un adaptador fresco. Respuesta `{ok, detail}` con detail categorizado ("credencial rechazada", "servicio no disponible", "conexión OK (N propiedades)") sin valores. En tests, los proveedores se doblan (sin gasto real).
- **Rationale**: reutiliza los clientes reales existentes; costo ~fracción de centavo en LLM aceptado por el host (assumption de la spec).

## R5. Modelo y migración

- **Decision**: `secret_entry` (name String(60) UNIQUE de lista cerrada, value_encrypted Text, hint String(8), timestamps) y `secret_change_log` (name, action Enum-str "set"/"deleted", hint, changed_at). Migración `e2f3a4b5c6d7` (down `d1e2f3a4b5c6`), sin enums de BD nuevos (action como String(12) — evita otro tipo global para 2 valores).
- **Alternatives considered**: reutilizar AgentAction (exige conversation_id — mismo motivo por el que 013 creó su tabla); genérico key-value sin lista cerrada (abre la puerta a guardar cualquier cosa sin consumidor — rechazado).

## R6. Arranque resiliente (FR-006/FR-012)

- **Decision**: lifespan de FastAPI carga la caché dentro de `try/except` (BD caída o tabla aún sin migrar → caché vacía + log de warning SIN valores; todo cae a entorno). `scan_daily` llama al mismo loader al inicio. Con BD vacía el comportamiento es byte-a-byte el actual.
