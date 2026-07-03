# Data Model: Precios y promociones por canal

**Feature**: 013-channel-pricing · **Date**: 2026-07-02

**Una migración mínima** (tabla de auditoría `channel_offset_log`); el resto activa un campo existente y extiende un JSON existente.

## Entidades

### `Channel` (existente — se activa `price_offset_pct`)

| Campo | Antes | Ahora |
|---|---|---|
| `price_offset_pct: Numeric(5,2) \| None` | Modelado sin uso (siempre NULL) | Ajuste % vigente del canal. `None` o `0` = sin ajuste (comportamiento actual). Gestionado SOLO vía preview→confirm→apply |

**Validación (servicio)**: `-50.00 ≤ pct ≤ 100.00`, 2 decimales. Solo canales con soporte del
CM (beds24: `airbnb`); para otros → error honesto, sin persistir.

**Invariante**: `price_offset_pct` refleja lo materializado en el CM. Si la escritura al CM
falla, NO se actualiza (y se abre SyncIssue). Verificación post-write por re-GET.

### `Promotion` (existente — alcance en `conditions` JSON)

| Clave JSON nueva | Tipo | Semántica |
|---|---|---|
| `conditions["channels_scope"]` | `list["booking"\|"airbnb"] \| ausente` | Canales donde aplica el fixed price. Ausente/None = todos (default y comportamiento actual) |

**Regla**: scope vacío `[]` es inválido (una promo debe aplicar al menos a un canal).

### Auditoría: `ChannelOffsetLog` (NUEVA, append-only — migración b7c8d9e0f1a2)

| Campo | Tipo | Notas |
|---|---|---|
| `channel_id` | FK → channel | canal ajustado |
| `before_pct` / `after_pct` | Numeric(5,2) \| None | valores del ajuste |
| `origin` | ChangeOrigin | chat/manual |
| `detail` | JSONB \| None | contexto (multiplier antes/después reportado por el CM) |
| `changed_at` | datetime | indexado |

Revertir = aplicar `before_pct` por el mismo flujo. (Se descartó reutilizar
`AgentAction`: exige conversation_id — solo cubre el chat.)

### `SyncIssue` (existente)

Nuevo uso: fallo/verificación fallida al escribir el multiplier (endpoint Alpha) →
`kind=publish_failure` (o el kind existente equivalente), `entity_ref="channel:airbnb"`.

## DTOs del puerto (no persistidos)

```
# nuevos métodos del puerto ChannelManager
get_channel_price_adjustment(property_external_id, channel: str) -> Decimal | None
    # factor actual (1.08) parseado del sufijo *<número> del multiplier; None = sin ajuste
set_channel_price_adjustment(property_external_id, channel: str, factor: Decimal | None) -> WriteResult
    # factor None = quitar el sufijo (restaurar prefijo base); preserva el prefijo SIEMPRE
supports_price_adjustment(channel: str) -> bool          # beds24: {"airbnb"}

# extensión de DTO existente
RemoteFixedPrice.channels: dict[str, bool] | None = None  # token → enable; None = no tocar
```

## Vistas derivadas (no persistidas)

- **Precio efectivo por canal**: `round(base × (1 + pct/100))` COP. Cálculo en web (desde
  offsets + calendario) y en el agente (tool). El calendario API no cambia su respuesta.
- **Offsets por canal**: `GET /pricing/channel-offsets` → `[{channel, offset_pct, supported}]`.

## Estados / transiciones

Offset: `sin ajuste (None/0)` ⇄ `ajustado (pct)` — cada transición con confirmación,
auditada y verificada contra el CM. Sin estados intermedios persistidos: si el apply
falla, el estado local no cambia.
