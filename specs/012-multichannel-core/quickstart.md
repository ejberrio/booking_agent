# Quickstart: verificar el núcleo multi-canal

**Feature**: 012-multichannel-core

## Tests (sin APIs reales)

```bash
cd apps/api && uv run pytest -q        # incluye test_sync_channels / agent / status
cd apps/web && npm run build           # verificación frontend
```

Escenarios cubiertos por dobles del Channel Manager:
1. Import con reservas de origen mixto (booking / airbnb / None) → `channel_kind` correcto; None → direct.
2. Re-import con reserva existente mal etiquetada → se corrige, sin duplicados.
3. `/status` → bloque `channels` con conteos por canal.
4. Tool `get_bookings` con `channel="airbnb"` → solo esas; sin filtro → todas con canal.
5. `system_prompt(active_channels=["booking","airbnb"])` → menciona ambos canales y la publicación multi-canal.

## Verificación en producción (post-deploy)

```bash
WEB="https://web-production-dfcaf.up.railway.app"

# 1) Estado por canal
curl -s -H "Cookie: session=ok" "$WEB/api/proxy/status" | python3 -m json.tool
#    → channels: booking y airbnb activos, con conteos

# 2) Re-import (corrige históricos): desde la web (Configuración → Sincronizar)
#    o POST al endpoint de sync existente; luego repetir (1) y validar conteos.

# 3) Agente: en el chat preguntar "¿qué reservas tengo de Airbnb?" y
#    "¿qué reservas tengo en agosto?" → distingue canales.

# 4) Dashboard: la vista principal muestra la tarjeta "Canales".
```

Nota: la primera reserva real de Airbnb (o una de prueba en el listing) sirve como
verificación E2E del token `channel="airbnb"`; hasta entonces el escenario Airbnb
queda cubierto por los dobles.
