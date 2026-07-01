# Contract: Puerto ChannelManager — fixed prices (promociones)

**Feature**: 011-api-promotions · Extiende `app/channels/base.py` e implementa en `beds24_v2.py`.

El dominio no conoce Beds24: habla con estos métodos del puerto. La implementación V2 los traduce a `/inventory/fixedPrices`.

## Tipos (puerto, provider-agnostic)

```python
@dataclass
class RemoteFixedPrice:
    external_id: int | None      # id del canal; None al crear
    offer_id: int
    room_id: str
    first_night: date
    last_night: date
    name: str
    price: Decimal               # roomPrice
    price_enabled: bool = True   # roomPriceEnable
    min_nights: int | None = None
```

## Métodos nuevos del puerto

| Método | Propósito | Canal (Beds24 V2) |
|---|---|---|
| `set_fixed_price(fp: RemoteFixedPrice) -> WriteResult` | Crear (sin `external_id`) o modificar (con `external_id`) una promo | `POST /inventory/fixedPrices` (array de 1; crear = sin `id`); devuelve `id` → `external_id` |
| `get_fixed_prices(room_id) -> list[RemoteFixedPrice]` | Leer promos existentes (reconciliación/estado) | `GET /inventory/fixedPrices?roomId&propertyId` |
| `disable_fixed_price(external_id) -> WriteResult` | Neutralizar (retirar) — `roomPriceEnable=false` sobre el `id` | `POST /inventory/fixedPrices` con `{id, roomPriceEnable:false}` |
| `get_offers(room_id, arrival, departure, occupancy) -> list[...]` *(opcional)* | Validar que la oferta designada existe/es pública | `GET /inventory/rooms/offers?propertyId&roomId&arrival&departure&numAdults` |

## Comportamiento

- **Auth**: reutiliza el token V2 cacheado del adaptador (refreshToken→token 24h). Header `token`.
- **Crear**: body `[{offerId, roomId, propertyId, firstNight, lastNight, name, roomPrice, roomPriceEnable:true, minNights?}]`, sin `id`. Respuesta 201 → extraer `id` del elemento creado → `external_id`.
- **Modificar/neutralizar**: mismo endpoint incluyendo `id`. Para neutralizar: `roomPriceEnable:false` (fallback: `roomPrice` ≥ base) → deja de descontar.
- **Errores**: clasificar como el resto del adapter (`AuthError`/`RateLimited`/`ChannelError`), redactando secretos. Un fallo NO rompe la petición del usuario: el servicio lo captura y crea `SyncIssue`.
- **Límite**: máx. 100 fixed prices/room (documentado); si se alcanza, error claro de dominio.

## Verificado en vivo (2026-07-01)

- `GET /inventory/fixedPrices` → 200 con nuestro token (lista vacía en la cuenta actual).
- `GET /inventory/rooms/offers` (con `arrival`+`departure`+`numAdults`) → 200; devuelve ofertas aplicables y precio.
- `POST /inventory/fixedPrices` documentado (crear=sin id, máx 100/room, 201). **No hay DELETE** → retirada por neutralización.
