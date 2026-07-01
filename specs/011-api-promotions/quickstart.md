# Quickstart / Validación: Gestión de promociones de precio vía API

**Feature**: 011-api-promotions

## Precondición (setup único en el dashboard de Beds24)

1. Crear/designar la **oferta de promociones** en el panel (Booking Page → Offers): un slot con `Enable = Always` (pública) y un nombre (p. ej. "Promociones"). Anotar su número (1–16).
2. Poner ese número en config/env: `BEDS24_PROMO_OFFER_ID=<n>` (api y scan si aplica).

> Sin esta oferta designada, la app guía a configurarla y no crea promociones (FR-014).

## Validación funcional (local o prod, vía proxy autenticado)

Cookie de sesión para pruebas: `-H "Cookie: session=ok"` (el middleware solo exige que exista).

### 1. Crear una promoción (preview → apply)

```bash
# Preview (no aplica nada)
curl -s -H "Cookie: session=ok" -H "Content-Type: application/json" \
  -X POST "$WEB/api/proxy/pricing/promotions/preview" \
  -d '{"unit_type_id":1,"first_night":"2027-01-15","last_night":"2027-01-31","name":"Vacaciones enero","discount_pct":20,"min_nights":3}'
# → base_price, price (20% off), saving, warnings[], fingerprint

# Apply (confirmación del host) → publica en el canal
curl -s -H "Cookie: session=ok" -H "Content-Type: application/json" \
  -X POST "$WEB/api/proxy/pricing/promotions/apply" \
  -d '{"unit_type_id":1,"first_night":"2027-01-15","last_night":"2027-01-31","name":"Vacaciones enero","price":280000,"discount_pct":20,"min_nights":3,"fingerprint":"…"}'
# → { id, status:"published", external_id, published:true }
```

### 2. Ver promociones

```bash
curl -s -H "Cookie: session=ok" "$WEB/api/proxy/pricing/promotions?unit_type_id=1"
# → lista con offer, fechas, price, saving, discount_pct, status
```

### 3. Editar / retirar

```bash
# Editar: mismo apply con "id" → modifica el mismo external_id
# Retirar (neutraliza + oculta)
curl -s -H "Cookie: session=ok" -H "Content-Type: application/json" \
  -X POST "$WEB/api/proxy/pricing/promotions/retire" -d '{"id":12,"confirm":true}'
# → { id:12, status:"retired" }
```

### 4. Por chat

- "crea una promoción del 15 al 31 de enero con 20% de descuento, mínimo 3 noches" → propuesta → confirmar.
- "¿qué promociones tengo?" → lista.
- "quita la promo de enero" → propuesta de retirada → confirmar.
- Verificar que el agente **no** confunde esto con un deal nativo de Booking (FR-012).

## Verificación de escritura real (acotada y reversible) — con confirmación del host

1. Crear una promo de prueba en la oferta designada, **fechas lejanas** (p. ej. dentro de +300 días) y descuento pequeño.
2. `GET /inventory/fixedPrices` (o la lista de la app) confirma que existe con su `external_id`.
3. **Retirar** inmediatamente (neutraliza: `roomPriceEnable=false`) → deja de descontar.
4. (Opcional) limpieza final del registro neutralizado en el dashboard (la API no borra).

> Nunca dejar una promo de prueba descontando. Documentado también en `docs/operations.md`.

## Criterios de aceptación cubiertos

- Crear/ver/editar/retirar con confirmación (SC-001, SC-002).
- Lista coincide con el canal (SC-003).
- Entradas inválidas rechazadas (SC-004).
- Fallo de publicación → `SyncIssue`, no rompe (SC-005).
- Auditoría con antes/después (SC-006).
