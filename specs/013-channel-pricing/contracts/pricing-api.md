# Contract: API de pricing — offsets por canal y alcance de promociones

**Feature**: 013-channel-pricing

## `GET /pricing/channel-offsets`

```json
{
  "offsets": [
    { "channel": "booking", "offset_pct": null, "supported": false, "is_active": true },
    { "channel": "airbnb",  "offset_pct": 8.0,  "supported": true,  "is_active": true }
  ]
}
```

- `offset_pct`: valor local vigente (`Channel.price_offset_pct`); null = sin ajuste.
- `supported`: si el CM permite materializar un ajuste para ese canal.

## `POST /pricing/channel-offsets/preview`

Body: `{ "channel": "airbnb", "offset_pct": 8.0 }` →

```json
{
  "channel": "airbnb",
  "current_pct": null,
  "new_pct": 8.0,
  "example": { "base": "350000", "effective": "378000" },
  "warnings": ["El canal está inactivo: el ajuste no tendrá efecto hasta reactivarlo"],
  "fingerprint": "abc123..."
}
```

- 422 si `offset_pct ∉ [-50, 100]`; 409/422 con mensaje honesto si `supported=false`
  ("Booking vende al precio base; ajusta el precio base o el offset de Airbnb").
- El `example` usa el precio base más próximo con datos (o 100000 si no hay).

## `POST /pricing/channel-offsets/apply`

Body: `{ "channel": "airbnb", "offset_pct": 8.0, "fingerprint": "abc123..." }` →

```json
{ "applied": true, "verified": true, "channel": "airbnb", "offset_pct": 8.0, "issue": null }
```

- Flujo: valida fingerprint → escribe al CM (puerto) → si `ok`: persiste
  `Channel.price_offset_pct`, audita (AgentAction) → si `verified=false` o fallo:
  SyncIssue y `issue` con el detalle; en fallo NO persiste.
- Quitar el ajuste: `offset_pct: 0` (o null) por el mismo flujo.

## Promociones: alcance de canales (extensión de Feature 011)

`POST /pricing/promotions/preview|apply` aceptan opcional:

```json
{ "channels_scope": ["booking"] }
```

- Ausente/null = todos los canales (comportamiento actual). `[]` → 422.
- `PromotionPreview` gana `channels_scope: list[str] | null` y una advertencia fija de
  doble descuento que menciona deals de Booking Y descuentos semanal/mensual de Airbnb.
- `GET /pricing/promotions`: cada promoción incluye `channels_scope` (null = todos).

## Criterios de aceptación

- Con offsets en 0/null y sin `channels_scope`, TODAS las respuestas existentes son
  idénticas a las actuales (FR-012 / SC-004).
- Apply sin preview previo (fingerprint inválido) → 409 (patrón existente).
