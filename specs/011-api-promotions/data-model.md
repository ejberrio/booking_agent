# Data Model: Gestión de promociones de precio vía API

**Feature**: 011-api-promotions · **Date**: 2026-07-01

## Entidad nueva: `Promotion`

Representa una promoción de precio gestionada por la app. Es la fuente de verdad de los metadatos que el canal no guarda (el % pedido, el origen, el estado, la auditoría) y referencia al fixed price del canal por `external_id`.

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int (PK) | id interno |
| `unit_type_id` | FK → `unit_type` | habitación/unidad (reutiliza el modelo existente) |
| `offer_id` | int | oferta designada del canal (1–16); de config `beds24_promo_offer_id` |
| `external_id` | int \| null | `id` del fixed price en el canal (Beds24); null hasta publicar |
| `name` | str | nombre de la promo (p. ej. "Vacaciones enero") |
| `first_night` | date | primera noche del rango |
| `last_night` | date | última noche del rango |
| `base_price` | Decimal | precio base de referencia al crear (para ahorro/%); moneda COP |
| `price` | Decimal | precio con descuento (absoluto) enviado al canal |
| `discount_pct` | Decimal \| null | % pedido por el host (si lo dio); solo informativo/display |
| `min_nights` | int \| null | estancia mínima propia de la promo (opcional) |
| `status` | enum `PromotionStatus` | ciclo de vida (ver abajo) |
| `created_at` / `updated_at` | datetime | timestamps (mixin existente) |

**Reglas de validación** (servicio):
- `price > 0` y `price < base_price` (es descuento, no encarece ni regala).
- `discount_pct ∈ (0, 100)` si se aporta.
- `first_night ≤ last_night` y `last_night ≥ hoy` (no en el pasado).
- `min_nights` (si se da) `≥ 1`.
- Solape: no dos promociones `active`/`published` en la misma `offer_id` con rangos que se cruzan sin confirmación explícita.

## Estados: `PromotionStatus`

```
draft ──apply──▶ publishing ──ok──▶ published
                      │
                      └──error──▶ sync_error   (SyncIssue registrada; visible como no publicada)

published ──retire(confirm)──▶ retiring ──ok──▶ retired   (fixed price neutralizado: roomPriceEnable=false)
published ──edit(confirm)────▶ publishing ─...            (modifica el mismo external_id)
retired   ──(oculta de activas; reversible re-creando/re-habilitando)
```

- `draft`: creada en propuesta, aún no confirmada/publicada (puede no persistirse hasta apply; ver contrato).
- `published`: fixed price activo en el canal (aplica descuento).
- `sync_error`: falló la publicación; hay `SyncIssue`; se muestra como no publicada.
- `retired`: neutralizada (deja de descontar) y oculta de las activas.

## Entidades existentes reutilizadas

- **`UnitType`**: la unidad a la que pertenece la promoción.
- **`AgentAction`** *(auditoría)*: cada create/edit/retire registra quién, cuándo, antes/después, origen (chat/manual). Reutiliza el registro de acciones del agente.
- **`SyncIssue`**: fallo de publicación/retirada al canal; alimenta el estado `sync_error` y el conteo de incidencias (ya expuesto en `/status`).
- **`RangeSelection`** *(esquema existente)*: reutilizado para expresar el rango de fechas (+ `min_nights` opcional) de forma coherente con precios/disponibilidad.

## Mapeo dominio → canal (`fixedPrice` de Beds24 V2)

| Dominio (`Promotion`) | Canal (`fixedPrice`) |
|---|---|
| `offer_id` | `offerId` |
| unidad (`unit_type`) | `roomId` (+ `propertyId`) |
| `first_night` / `last_night` | `firstNight` / `lastNight` |
| `name` | `name` |
| `price` | `roomPrice` (+ `roomPriceEnable=true`) |
| `min_nights` | `minNights` (si aplica) |
| — (retirada) | `roomPriceEnable=false` (neutralizar) sobre el `id`=`external_id` |
| `external_id` | `id` (devuelto al crear; requerido para editar/retirar) |

`discount_pct` y `base_price` **no** tienen equivalente en el canal (no hay campo %): viven solo en nuestra BD.

## Nota de implementación (reconciliación con el modelo existente)

Durante `implement` se encontró que **ya existía** un modelo `Promotion` (features
003/009) para "promociones internas" que recortan el precio base del calendario. Para
no duplicar el concepto (Principio V), se **reutilizó y extendió** ese modelo en vez de
crear uno nuevo:

- Se **añadieron** columnas nullable: `unit_type_id` (FK), `offer_id`, `external_id`.
- Se **reutilizaron** `start_date`/`end_date` como rango (first/last night), y
  `discount_type=percent`/`discount_value` para guardar el % pedido.
- `base_price`, `price` (absoluto) y `min_nights` se guardan en la columna JSON
  `conditions` (junto a `published: bool`).
- Se **reutilizó** el enum `PromotionStatus` existente (`active`=viva, `inactive`=retirada);
  el estado `sync_error` se deriva de `conditions.published=false` + `SyncIssue` (no se
  amplió el enum, evitando una migración de tipo).
- La vía "oferta" vive en `offer_promotion_service`; el `promotion_service` clásico se
  conserva intacto. Una promoción es "de oferta" cuando `offer_id` no es null.

## Migración

- Alembic: nueva tabla `promotion` + enum `promotionstatus` (patrón `postgresql.ENUM(create_type=False)` si el enum ya existiera, como en 008). Encadenada tras la última migración (`7d3816a7c205`).
