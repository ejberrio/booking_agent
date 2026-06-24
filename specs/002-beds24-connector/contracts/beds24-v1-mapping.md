# Mapeo — Beds24 API V1 (JSON)

Cómo el adaptador (`app/channels/beds24.py`) traduce el puerto `ChannelManager` a la API V1 de Beds24. Base: `https://api.beds24.com/json/`. Autenticación: cada petición POST incluye `{"authentication": {"apiKey": "<BEDS24_API_KEY>"}}` (sin propKey, propiedad propia). Los nombres/campos exactos se confirman contra la documentación oficial de Beds24 durante la implementación.

| Operación del puerto | Endpoint V1 | Entrada (resumen) | Salida → DTO |
|----------------------|-------------|-------------------|--------------|
| `test_connection` | `getProperties` | authentication | `ConnectionInfo` (ok + propiedades) |
| `get_properties` | `getProperties` | authentication, includeRooms | `list[RemoteProperty]` (con `RemoteRoom`) |
| `get_rates` | `getRoomDates` | propId, roomId, from, to | `list[RemoteRate]` (price, available por fecha) |
| `get_bookings` | `getBookings` | propId, (modifiedSince) | `list[RemoteBooking]` |
| `set_rate` | `setRoomDates` | propId, roomId, dates:{YYYY-MM-DD:{price1}} | `WriteResult` (+ relectura para verificar) |
| `set_rate_range` | `setRoomDates` | propId, roomId, rango de fechas con price | `WriteResult` (+ relectura) |

## Notas de implementación
- **Identificadores**: `propId` y `roomId` (de la feature 001 `external_ref`; valores actuales del host: propId 337229, roomId 697411) se pasan en las llamadas. No son secretos.
- **Escritura verificada**: tras `setRoomDates`, llamar `getRoomDates` del mismo rango y comparar el precio aplicado (C3 del puerto).
- **Rate limit / errores**: Beds24 responde con un campo de error en el JSON; el adaptador lo traduce a `AuthError` / `RateLimited` / `ChannelError` y reintenta con backoff cuando corresponde.
- **Disponibilidad**: `getRoomDates` también trae disponibilidad → alimenta `CalendarDay` (compartida por unidad).
- **Sin propKey**: la API Key de cuenta con *Allow Writes = Yes* autoriza escrituras sobre la propiedad propia.
- **Secretos**: la `apiKey` se inyecta desde env en el cuerpo de la petición; nunca se registra en logs.
- **Migración futura a V2**: el mismo puerto se reimplementaría con endpoints REST V2 + token; el `sync_service` no cambia.
