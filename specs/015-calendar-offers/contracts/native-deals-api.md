# Contract: API de deals nativos + advertencia real de doble descuento

**Feature**: 015-calendar-offers

## `GET /pricing/native-deals`

Lista completa (activos e inactivos; el cliente filtra para el calendario), orden estable (channel, date_from NULLS FIRST, id):

```json
{
  "deals": [
    {
      "id": 1,
      "channel": "booking",
      "name": "Vacaciones Julio · mín 3",
      "discount_pct": "20.00",
      "date_from": "2026-07-03",
      "date_to": "2026-07-31",
      "is_active": true
    },
    {
      "id": 2,
      "channel": "airbnb",
      "name": "Descuento semanal",
      "discount_pct": "5.00",
      "date_from": null,
      "date_to": null,
      "is_active": true
    }
  ]
}
```

## `POST /pricing/native-deals`

Body: `{ "channel": "booking", "name": "...", "discount_pct": 20, "date_from": "2026-07-03" | null, "date_to": "2026-07-31" | null }` → 200 con el deal creado.

- **422**: canal ∉ {booking, airbnb}; nombre vacío; pct ∉ [0,100]; date_from > date_to. Mensajes claros en `detail`.

## `PATCH /pricing/native-deals/{id}`

Body parcial (cualquier campo, incl. `is_active` para desactivar/reactivar; `date_from`/`date_to` aceptan null explícito para abrir el extremo) → 200 con el deal actualizado. 404 si no existe; 422 misma validación.

## `DELETE /pricing/native-deals/{id}`

→ 200 `{"deleted": true}`. 404 si no existe. Borrado real (es una anotación, no auditoría).

**Garantía transversal**: ninguna operación de este CRUD llama al Channel Manager.

## Advertencia real de doble descuento (extensión del preview existente)

`POST /pricing/promotions/preview` (y `apply`, y el tool `propose_offer_promotion` del agente — mismo servicio): `warnings` gana una entrada POR CADA deal nativo activo que solape en fechas y canal:

```
"Puede duplicar descuento con el deal nativo 'Vacaciones Julio · mín 3' (Booking.com, 20%). Revísalo antes de confirmar."
```

- Sin deals que solapen (fechas fuera, canal excluido por `channels_scope`, o deal inactivo) → NINGUNA advertencia de doble descuento (cero falsas alarmas).
- Deal "siempre activo" → advierte para cualquier rango de su canal.
- No bloquea: sigue siendo warning (combinar a propósito es decisión del host).

## Web (contratos de UI)

- `lib/types.ts`: `NativeDeal`; `lib/api.ts`: `listNativeDeals/createNativeDeal/updateNativeDeal/deleteNativeDeal`.
- `PriceCalendar`: prop opcional `nativeDealDates?: Set<string>` → punto cian + leyenda "Deal nativo" (solo si hay); sin la prop, render idéntico.
- `OffersPanel` (nuevo): promos de la app (nombre, %, alcance de canales, rango) + deals (nombre, canal, %, vigencia o "siempre activo") del día seleccionado; solo aparece si el día tiene ofertas.
- Sección Ofertas: tarjeta "Deals nativos registrados" (lista + alta + editar + interruptor activo + borrar) integrada con la guía existente.

## Criterios de aceptación

- CRUD completo funcional con validaciones (422 con mensaje claro).
- Preview con deal solapante → warning con nombre/canal/%; sin solape → sin warning nuevo (los warnings existentes de promos/reservas intactos).
- Con registro vacío: respuestas y render byte-a-byte como hoy (FR-010/SC-004; 187 tests verdes).
