# Contrato: API de disponibilidad

Endpoints REST (consumidos por el calendario web). Análogos a los de precios por rango.

## POST /pricing/availability/preview

Body:
```json
{ "unit_type_id": 1, "action": "block" | "open",
  "selection": { "date_from": "2026-07-01", "date_to": "2026-07-03", "weekdays": [5,6] } }
```
Respuesta:
```json
{
  "action": "block",
  "days": [
    { "date": "2026-07-01", "old_available": 1, "new_available": 0, "valid": true,  "skip_reason": null },
    { "date": "2026-07-02", "old_available": 0, "new_available": 0, "valid": false, "skip_reason": "reservada" }
  ],
  "affected_count": 1,
  "skipped_count": 1,
  "reinforced": false,
  "fingerprint": "..."
}
```
- `valid=false` + `skip_reason` para noches omitidas (reservada, o ya en el estado destino).
- `fingerprint`: huella del estado previsto (detección de obsolescencia, como en precios).

## POST /pricing/availability/apply

Body:
```json
{ "unit_type_id": 1, "action": "block" | "open",
  "selection": { "date_from": "...", "date_to": "...", "weekdays": [5,6] },
  "fingerprint": "..." }
```
Respuesta:
```json
{ "affected": ["2026-07-01"], "skipped": [{"date":"2026-07-02","reason":"reservada"}],
  "audited": 1, "published": 1, "publish_issues": 0, "stale": false }
```
- Aplica local (CalendarDay + AvailabilityChangeLog) y publica a Beds24 (numAvail).
- `publish_issues>0` si la publicación falló (incidencia registrada; cambio local conservado).
- `stale=true` si el fingerprint no coincide (el estado cambió desde el preview) → no aplica.

## GET /pricing/calendar (ampliado)

Cada día incluye además el estado de disponibilidad para que el frontend distinga **bloqueada** de **reservada**:
```json
{ "date": "...", "base_price": ..., "available": 0|>0|null, "is_blocked": true|false, "promotions": [] }
```
(`is_blocked` nuevo; `available=null` = sin datos.)

## Reglas

- Nunca altera noches con reserva confirmada.
- Publicación resiliente (incidencia si Beds24 falla).
- Sin secretos en respuestas/errores.
