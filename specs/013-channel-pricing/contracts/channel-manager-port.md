# Contract: puerto ChannelManager — ajuste por canal y alcance de fixed prices

**Feature**: 013-channel-pricing

## Métodos nuevos del puerto (`app/channels/base.py`)

```python
def supports_price_adjustment(self, channel: str) -> bool: ...
    # ¿El CM permite ajuste de precio para este canal? (beds24: solo "airbnb")

async def get_channel_price_adjustment(
    self, property_external_id: str, channel: str
) -> Decimal | None: ...
    # Factor vigente (p. ej. Decimal("1.08")); None = sin ajuste propio.

async def set_channel_price_adjustment(
    self, property_external_id: str, channel: str, factor: Decimal | None
) -> WriteResult: ...
    # factor=None quita el ajuste. verified=True solo si el re-GET confirma el valor.
```

**Neutralidad**: el dominio habla en `factor: Decimal`; la fórmula del multiplier
(`*[CONVERT:COP-USD]*1.08`) es un detalle del adaptador Beds24 y NUNCA cruza el puerto.

## Obligaciones del adaptador Beds24 V2

- `GET /channels/settings?propertyId=...&channel[]=airbnb` → leer `multiplier` (string).
- **Parseo**: el sufijo `*<número>` final (regex `\*(\d+(?:\.\d+)?)$`) es NUESTRO factor;
  todo lo anterior es el **prefijo base** del operador (p. ej. `*[CONVERT:COP-USD]`) y es
  INTOCABLE. Sin sufijo numérico ⇒ factor None.
- **Escritura**: `POST /channels/settings` body
  `[{"channel": "airbnb", "properties": [{"id": <propId>, "multiplier": "<prefijo>[*<factor>]"}]}]`
  con factor a 4 decimales. Endpoint **Alpha** ⇒ tras el POST, re-GET y comparar; si no
  coincide → `WriteResult(ok=True, verified=False, detail=...)`.
- `supports_price_adjustment`: True solo para `"airbnb"` (y futuros del enum del endpoint).

## Extensión de `RemoteFixedPrice`

```python
channels: dict[str, bool] | None = None   # token neutro → enable; None = no tocar
```

- `_fixed_price_body`: si `channels` no es None, añadir
  `"channels": {token: {"enable": flag} for token, flag in channels.items()}`.
  Solo se envían los tokens presentes (los demás canales del CM no se alteran).
- ⚠️ Clave **`enable`** (payload real observado), no `enabled` (yaml). Si el POST la
  rechazara en la verificación en vivo, probar `enabled` y documentar.

## Casos de prueba del contrato

1. GET multiplier `"*[CONVERT:COP-USD]"` → factor None; `"*[CONVERT:COP-USD]*1.08"` → 1.08.
2. set(1.08) sobre prefijo `*[CONVERT:COP-USD]` → escribe `*[CONVERT:COP-USD]*1.08`; re-GET igual ⇒ verified.
3. set(None) → escribe exactamente el prefijo; multiplier sin sufijo.
4. set sobre canal no soportado ("booking") → el SERVICIO lo bloquea antes (el adaptador puede lanzar).
5. Multiplier vacío/None en el CM + set(1.05) → escribe `*1.05` (prefijo vacío).
6. fixed price con scope solo-booking → body incluye `"channels": {"airbnb": {"enable": false}}` y nada más.
