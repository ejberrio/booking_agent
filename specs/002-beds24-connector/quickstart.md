# Quickstart — Conector Beds24

Cómo configurar y verificar el conector una vez implementado (`/speckit-implement`).

## 1. Configurar credenciales (local, fuera del repo)

En `apps/api/.env` o el `.env` raíz (gitignored):
```bash
CHANNEL_MANAGER=beds24
BEDS24_API_KEY=<tu API Key 1 de Beds24, con Allow Writes = Yes>
BEDS24_PROP_ID=337229
BEDS24_ROOM_ID=697411
BEDS24_BASE_URL=https://api.beds24.com/json
```
En Beds24 → Account Access: API Key 1 con **API Key Access ≠ disabled** y **Allow Writes = Yes**, luego **Save**.

## 2. Migraciones (nuevas tablas de operación)

```bash
cd apps/api
uv run alembic revision --autogenerate -m "conector beds24 (sync)"
uv run alembic upgrade head
```

## 3. Verificación funcional

```bash
make api   # API en :8000
```
1. **Probar conexión**: `POST /sync/test` → confirma acceso y lista las propiedades de la cuenta (o error claro si la key es inválida).
2. **Importar**: `POST /sync/import` → propiedades, unidades, calendario, precios y reservas quedan en el modelo local con su `external_ref`. Re-ejecutar no duplica (incremental).
3. **Publicar**: fijar un precio local (feature 001) y `POST /sync/publish` → el precio llega a Beds24 y se verifica; queda auditado en local.
4. **Revisar corridas**: `GET /sync/runs` → estado, conteos e incidencias (`SyncIssue`).
5. **Discrepancia**: cambiar un precio directamente en Beds24 y re-importar → se crea un `SyncIssue(price_discrepancy)` sin sobrescribir el local.

## 4. Sincronización diaria (cron)

```bash
# Ejemplo de crontab (servidor): 06:00 diario
0 6 * * *  cd /ruta/apps/api && uv run python -m scripts.sync_daily
```

## 5. Tests (sin API real)

```bash
cd apps/api
uv run pytest -q        # incluye test_beds24_adapter (httpx mock) y test_sync_service
uv run ruff check .
```
Criterio de aceptación: tests del contrato (`contracts/channel-manager-port.md`) en verde, sin llamadas a la API real ni secretos en logs.
