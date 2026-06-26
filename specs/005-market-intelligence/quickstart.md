# Quickstart — Inteligencia de mercado y sugerencias

Cómo usar y verificar la feature una vez implementada (`/speckit-implement`).

## 1. Migración (tablas nuevas)

```bash
cd apps/api
uv run alembic revision --autogenerate -m "intelligence run + market reference"
uv run alembic upgrade head
```

## 2. Configuración

- `SEARCH_PROVIDER=tavily` y `SEARCH_API_KEY` en `.env` (ya configurado).
- `OPENAI_API_KEY` para el parsing de eventos (ya configurado).
- Requiere propiedad/unidad con precios (003) y, opcionalmente, una fila en `market_reference` por zona.

## 3. Flujo (con la API corriendo)

```bash
make api   # :8000
```
1. **Escaneo** (cron o manual): busca eventos en Medellín, los parsea con el LLM, deduplica, y genera sugerencias para el horizonte.
2. **Revisar**: `GET /suggestions` → lista con día/rango, precio sugerido, justificación y confianza.
3. **Aprobar/Aplicar**: `POST /suggestions/{id}/apply` → fija el precio (origen=sugerencia), audita y publica el efectivo a Beds24; o `POST /suggestions/{id}/reject`.
4. **Por chat**: "¿qué me sugieres para agosto?" → el agente usa la herramienta `get_suggestions`.
5. **Cron**:
   ```bash
   0 5 * * *  cd /ruta/apps/api && uv run python -m scripts.scan_daily
   ```

## 4. Tests (sin APIs reales ni créditos)

```bash
cd apps/api
uv run pytest -q     # test_suggestion_engine (heurística pura) + test_intelligence_service (dobles)
uv run ruff check .
```
Criterio: contratos de `contracts/intelligence-contract.md` en verde; cero llamadas reales a Tavily/LLM/Beds24; ninguna sugerencia aplicada sin aprobación.
