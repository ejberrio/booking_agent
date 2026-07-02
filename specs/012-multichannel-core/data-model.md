# Data Model: Núcleo multi-canal

**Feature**: 012-multichannel-core · **Date**: 2026-07-02

**Sin cambios de esquema.** Los modelos ya son channel-aware (feature 001); esta feature cambia *cómo se llenan*.

## Entidades reutilizadas

### `Booking` (existente — cambia el llenado, no el esquema)

| Campo | Antes | Ahora |
|---|---|---|
| `channel_kind: ChannelKind` | Siempre `booking` (hardcoded en el import) | Canal real reportado por el canal manager, normalizado |

**Regla de normalización** (`sync_service._map_channel`):

```
token del puerto (RemoteBooking.channel)  →  ChannelKind
"booking", "booking.com", "bookingcom"    →  booking
"airbnb", "airbnb.com"                    →  airbnb
None / no reconocido                      →  direct   (nunca aborta el lote)
```

**Regla de corrección (re-import)**: si la reserva existe (`external_ref` match) y
`channel_kind` difiere del reportado → se actualiza (cuenta en `updated_count` del
`SyncRun`). La des-duplicación por `external_ref` se mantiene ⇒ 0 duplicados.

### `Channel` (existente — cambia el llenado)

| Campo | Antes | Ahora |
|---|---|---|
| filas | Solo `kind=booking` (creada en `_upsert_property`) | Una fila por kind en `CHANNELS_ACTIVE` (default `booking,airbnb`), `is_active=True`; kinds registrados fuera de la config → `is_active=False` |
| `price_offset_pct` | sin uso | **sigue sin uso** (Feature 013) |

Constraint existente `uq_channel_property_kind` garantiza una fila por (propiedad, kind).

### `RemoteBooking` (DTO del puerto — único cambio estructural, no persistido)

```
RemoteBooking:
  external_id: str
  room_external_id: str
  check_in: date
  check_out: date
  status: str = "confirmed"
  channel: str | None = None    # NUEVO: token neutro en minúsculas; None = no reportado
```

Default `None` ⇒ dobles y llamadas existentes siguen compilando (compatibilidad).

## Configuración

| Setting | Default | Semántica |
|---|---|---|
| `channels_active` (`CHANNELS_ACTIVE`) | `"booking,airbnb"` | CSV de `ChannelKind` conectados en el canal manager; gobierna el upsert de `Channel` y el prompt del agente |

## Vistas derivadas (no persistidas)

- **`/status.channels`**: `[{kind, is_active, bookings: count(Booking.channel_kind=kind, status=confirmed)}]`.
- **Prompt del agente**: lista de kinds activos inyectada al system prompt.

## Estados / transiciones

Sin máquinas de estado nuevas. `Channel.is_active` transiciona solo por cambio de
configuración + import (activo ⇄ inactivo); las reservas históricas del canal
desactivado se conservan intactas.
