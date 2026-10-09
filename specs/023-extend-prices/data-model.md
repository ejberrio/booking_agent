# Data Model: 023

Sin tablas nuevas.

## Cambios
- `ChangeOrigin.extension` (enum `changeorigin`): origen de auditoría de precios y disponibilidad escritos por la extensión.
- `rate`: se borran las filas con `base_price <= 0` (migración). Invariante nueva: nunca se guarda `Rate` ≤ 0.

## Objetos de vista (no persistidos)
- `ExtensionMonthInput {month: "YYYY-MM", price?: Decimal > 0, included: bool = true}`
- `ExtensionParams {unit_type_id, until?: date, weekend_pct: 0..50 = 0, open_closed: bool = true, months?: [ExtensionMonthInput]}`
- `ExtensionNight {date, price, weekend, clipped: "min"|"max"|null, open: bool, kept_closed: bool}`
- `ExtensionMonth {month, proposed_price, price, included, nights, weekend_nights, weekday_price, weekend_price, to_open, kept_closed, clipped_min, clipped_max}`
- `ExtensionPreview {until, first_target, min_price, max_price, weekend_pct, open_closed, months[], total_nights, total_to_open, fingerprint}`
- `ExtensionResult {stale, months: [{month, status: applied|failed|skipped, nights, opened, detail}], applied_nights, opened_nights, failed_months}`
- `HorizonStatus {first_unpriced_night: date|null, months_covered: int, needs_extension: bool, default_until, max_until}`

## Puerto
- `CalendarEntry(date_from, date_to, price: Decimal, num_avail: int | None)`
- `ChannelManager.set_calendar_entries(room_external_id, entries) -> WriteResult`
