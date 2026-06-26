# Quickstart — Agente conversacional

Cómo usar y verificar el agente una vez implementado (`/speckit-implement`).

## 1. Migración (tabla de acciones del agente)

```bash
cd apps/api
uv run alembic revision --autogenerate -m "agent action"
uv run alembic upgrade head
```

## 2. Configuración

- `OPENAI_API_KEY` en `.env` (ya configurada). `LLM_MODEL=gpt-4o-mini`, `LLM_MODEL_ACTIONS=gpt-4o`.
- Requiere una propiedad/unidad importada (feature 002) y precios cargados (feature 003).

## 3. Conversación (con la API corriendo)

```bash
make api   # :8000
```
Ejemplos por `POST /chat` (o SSE en `/chat/stream`):
1. **Consulta**: "¿cuánto cuesta el 15 de julio?" → el agente llama `get_calendar` y responde con el precio efectivo real.
2. **Cambio (propuesta)**: "sube 20% los fines de semana de agosto" → el agente responde una **propuesta** (días afectados, antes/después) y NO aplica; si supera el umbral, lo marca como cambio grande.
3. **Confirmar**: "sí" → aplica, audita (origen=chat), publica el efectivo a Beds24; responde el resultado.
4. **Re-proponer**: si el estado cambió entre la propuesta y el "sí", el agente vuelve a proponer.
5. **Cancelar**: "no" / cambiar de tema → no aplica nada.
6. **Promoción**: "crea una promo del 10% la próxima semana" → propone → confirmas → se crea y re-publica.

## 4. Tests (sin tokens reales ni API de Beds24)

```bash
cd apps/api
uv run pytest -q     # test_agent_orchestrator con FakeLLM (tool-calls guionizados) + ChannelManager falso
uv run ruff check .
```
Criterio: contratos de `contracts/agent-contract.md` en verde; cero llamadas reales al LLM o a Beds24; ninguna escritura sin confirmación.
