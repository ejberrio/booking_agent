# Contract: puerto ChannelManager — canal de origen en reservas

**Feature**: 012-multichannel-core

## Cambio en el DTO `RemoteBooking` (`app/channels/base.py`)

```python
@dataclass(frozen=True)
class RemoteBooking:
    external_id: str
    room_external_id: str
    check_in: date
    check_out: date
    status: str = "confirmed"
    channel: str | None = None   # NUEVO
```

### Semántica de `channel`

- Token **neutro** en minúsculas que identifica el canal de venta de origen
  (p. ej. `"booking"`, `"airbnb"`). No es un valor propietario del proveedor.
- `None` cuando el proveedor no reporta origen (p. ej. reserva manual en el panel).
- El **dominio** decide el mapeo a `ChannelKind` (el puerto NO importa enums del dominio).

### Obligaciones del adaptador

| Adaptador | Fuente del token | Regla |
|---|---|---|
| `Beds24V2Adapter` | `b["channel"]`; fallback `b["referer"]` | lowercase; si `referer` contiene "booking" → `"booking"`, contiene "airbnb" → `"airbnb"`; si nada → `None`. Nunca lanzar por este campo |
| `Beds24Adapter` (V1, legacy lectura) | `b["referer"]` | misma regla de fallback; si falta → `None` |

### Compatibilidad

- Campo con default ⇒ constructores existentes (tests, dobles) no cambian.
- Puerto `ChannelManager`: **sin cambios de firma** en métodos.

## Verificación (dato real, 2026-07-02)

`GET /v2/bookings?propertyId=337229` devolvió la reserva real con
`{"referer": "Booking.com", "channel": "booking", "apiSourceId": 19}` — `channel` es
el campo estable a usar.
