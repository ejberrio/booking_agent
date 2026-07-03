# Contract: API de reservas (lectura) y notas de calendario

**Feature**: 016-calendar-bookings-notes

## `GET /bookings?unit_type_id&date_from&date_to`

Reservas CONFIRMADAS cuya estancia solapa el rango (noches `[check_in, check_out)`), orden por check_in:

```json
{
  "bookings": [
    {
      "id": 4,
      "guest_name": "John Doe",
      "channel": "booking",
      "check_in": "2026-08-06",
      "check_out": "2026-08-19",
      "nights": 13,
      "status": "confirmed",
      "external_ref": "75333844"
    }
  ]
}
```

- `guest_name` puede ser `null` → la UI muestra "sin nombre" (honesto).
- Sin escrituras; el nombre no aparece en logs (middleware existente no registra cuerpos).

## `GET /calendar-notes?unit_type_id`

```json
{ "notes": [ { "id": 1, "unit_type_id": 1, "date_from": "2026-10-19", "date_to": "2026-10-21", "text": "Reserva personal de Fulano" } ] }
```

## `POST /calendar-notes`

Body: `{ "unit_type_id": 1, "date_from": "...", "date_to": "...", "text": "..." }` → 200 con la nota.

- **422**: texto vacío o >500; `date_from > date_to`. `detail` claro.

## `PATCH /calendar-notes/{id}`

Body parcial (`text`, `date_from`, `date_to`) → 200 con la nota. 404 inexistente; 422 validación.

## `DELETE /calendar-notes/{id}`

→ 200 `{"deleted": true}`. 404 si no existe. Borrado real (memoria del host, no auditoría).

**Garantía transversal**: ningún endpoint de esta feature llama al Channel Manager.

## Import (extensión del puerto)

`RemoteBooking.guest_name: str | None`; Beds24 V2 compone `firstName + lastName` (parciales OK; vacío → None); import: crear → set, existente → corrige si remoto no vacío ≠ local (nunca borra con silencio remoto); cuenta en `updated_count`.

## Web (contratos de UI)

- `lib/types.ts`: `BookingView`, `CalendarNote`; `lib/api.ts`: `listBookings(unitTypeId, from, to)`, `listCalendarNotes(unitTypeId)`, `createCalendarNote/updateCalendarNote/deleteCalendarNote`.
- `PriceCalendar`: prop opcional `noteDates?: Set<string>` → punto lima + leyenda "Nota"; sin la prop, render idéntico.
- `DayInfoPanel` (nuevo): con selección de UN día → sección "Reservas" (si hay: huésped o "sin nombre", canal display, llegada → salida, noches, estado, ref); con cualquier selección → sección "Notas": notas que cubren el rango (editar/borrar) + crear nota sobre TODA la selección.

## Criterios de aceptación

- Reserva ago 6-19: clic en ago 6 y ago 18 la muestran; ago 19 (día de salida) NO.
- Re-import con dobles que ahora reportan nombre → histórica corregida (`updated_count`).
- CRUD de notas validado (422 con mensaje); solapes permitidos; días con nota — y solo esos — con punto lima.
- Con cero notas y nombres vacíos: render y respuestas idénticos (199 tests verdes).
