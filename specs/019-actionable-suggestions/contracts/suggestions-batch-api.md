# Contract: API de sugerencias accionables (019)

Todos los endpoints viven bajo `/suggestions` (proxy web `/api/proxy/suggestions/...`). Errores con `detail` en español.

## GET /suggestions/blocks?unit_type_id={id?}

Sugerencias pendientes (`proposed|approved`) reducidas a sus **noches vendibles** y agrupadas en bloques. Solo lectura.

```json
{
  "blocks": [
    {
      "key": "event:juanes",
      "kind": "event",
      "title": "Juanes",
      "date_from": "2026-11-14",
      "date_to": "2026-11-16",
      "direction": "up",
      "suggestion_ids": [2122, 2123],
      "nights": [
        {"date": "2026-11-14", "suggestion_id": 2122, "current_price": "470000.00", "suggested_price": "611000.00"},
        {"date": "2026-11-16", "suggestion_id": 2123, "current_price": "470000.00", "suggested_price": "611000.00"}
      ],
      "suggestions": [
        {"id": 2122, "date_from": "2026-11-14", "date_to": "2026-11-14", "suggested_price": "611000.00",
         "rationale": {"text": "…", "factors": []}, "confidence": "0.500",
         "total_nights": 1, "sellable_count": 1, "occupied_count": 0}
      ]
    }
  ],
  "hidden_occupied": 3
}
```

- `hidden_occupied`: noches de sugerencias pendientes ocultas por estar reservadas/bloqueadas (informativo).
- Sugerencias sin noches vendibles no aparecen.
- `key`: `event:<nombre normalizado>` o `period:<gap|occupancy|other>:<fecha inicio>`.

## POST /suggestions/batch/preview

```json
{"suggestion_ids": [2122, 2123, 2166]}
```

200:

```json
{
  "suggestion_ids": [2122, 2123, 2166],
  "items": [
    {"date": "2026-10-15", "suggestion_id": 2166, "old_price": "270000.00", "new_price": "287000.00", "valid": true, "reason": null},
    {"date": "2026-10-16", "suggestion_id": 2166, "old_price": "270000.00", "new_price": "287000.00", "valid": false, "reason": "reservada"}
  ],
  "valid_count": 1,
  "skipped_count": 1,
  "fingerprint": "a1b2c3d4e5f60718"
}
```

- 422 si `suggestion_ids` está vacío. Ids inexistentes o ya resueltos → sus noches salen con `reason: "sugerencia resuelta"` (no error), para que la vista previa sea honesta.
- `reason ∈ {"reservada", "bloqueada", "pasada", "fuera de límites", "sugerencia resuelta", "conflicto"}`.

## POST /suggestions/batch/apply

```json
{"suggestion_ids": [2122, 2123, 2166], "fingerprint": "a1b2c3d4e5f60718"}
```

200:

```json
{
  "nights": [
    {"date": "2026-10-15", "suggestion_id": 2166, "status": "applied", "reason": null},
    {"date": "2026-10-16", "suggestion_id": 2166, "status": "skipped", "reason": "reservada"}
  ],
  "applied_count": 1,
  "skipped_count": 1,
  "failed_count": 0,
  "suggestions": {"2122": "applied", "2123": "applied", "2166": "applied"}
}
```

- **409** `{"detail": "La vista previa cambió (precios, reservas o sugerencias); revísala de nuevo."}` si la huella no coincide. No se escribe nada.
- Noches `failed` (publicación al canal con incidencias): su tramo se revierte localmente, se registra una incidencia de sincronización y la sugerencia sigue pendiente (`"pending"`).
- `suggestions[id]`: `applied` (≥1 aplicada y 0 fallidas) · `pending` (alguna fallida) · `unchanged` (todas omitidas).

## Sin cambios

`GET /suggestions`, `GET /suggestions?pending=true`, `POST /suggestions/{id}/apply`, `POST /suggestions/{id}/reject` mantienen su contrato (014/018). El calendario sigue usando `GET /suggestions?status=proposed`.
