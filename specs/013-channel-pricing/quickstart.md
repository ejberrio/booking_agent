# Quickstart: verificar precios y promociones por canal

**Feature**: 013-channel-pricing

## Tests (sin APIs reales)

```bash
cd apps/api && uv run pytest -q       # adaptador (multiplier/channels), servicio, promos scope, agente
cd apps/web && npm run build
```

Escenarios clave con dobles:
1. Parseo/composición del multiplier preservando `*[CONVERT:COP-USD]` (set/get/quitar).
2. Rango del offset [−50, 100]; canal no soportado → error honesto; fingerprint obligatorio.
3. Apply verifica con re-GET; discrepancia → SyncIssue y sin persistencia local.
4. Promoción con `channels_scope=["booking"]` → body con `{"airbnb": {"enable": false}}`; sin scope → body sin `channels`.
5. Con offsets 0/null: respuestas idénticas a las actuales (FR-012).

## Verificación EN VIVO (acotada y reversible — con confirmación del host)

```bash
WEB="https://web-production-dfcaf.up.railway.app"

# 1) Estado inicial
curl -s -H "Cookie: session=ok" "$WEB/api/proxy/pricing/channel-offsets" | python3 -m json.tool

# 2) Offset de prueba PEQUEÑO en Airbnb (+2%): preview → apply (vía app o curl)
#    Verificar: GET /channels/settings en Beds24 muestra "*[CONVERT:COP-USD]*1.02"
#    y el multicalendario de Airbnb sube ~2% (dar minutos a Airbnb).

# 3) REVERTIR: offset 0 → multiplier vuelve EXACTO a "*[CONVERT:COP-USD]".
#    ⚠️ Nunca dejar un offset de prueba aplicado.

# 4) Promoción de prueba con alcance "solo booking", fechas lejanas (+300 días),
#    verificar en GET /inventory/fixedPrices que channels.airbnb.enable=false,
#    RETIRAR de inmediato (neutralizar) — patrón de la Feature 011.

# 5) Ofertas (web): alcance visible en preview/lista; deep-links de Airbnb funcionan.
```

Decisión del host pendiente para producción: ¿dejar Airbnb en 0% (como hoy) o aplicar
un offset real? La feature entrega el control; el valor es decisión de negocio.
