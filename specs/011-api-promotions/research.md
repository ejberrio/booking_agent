# Research: Gestión de promociones de precio vía API

**Feature**: 011-api-promotions · **Date**: 2026-07-01

Todas las decisiones parten de la verificación en vivo del 2026-07-01 (lectura del OpenAPI oficial `apiV2.yaml` de Beds24 y pruebas con nuestro token real de solo lectura).

## D1 — Endpoint de escritura de promociones

- **Decisión**: usar `POST /inventory/fixedPrices` (Inventory) para crear/modificar promociones. Cuerpo = **array** de objetos `fixedPrice`; para **crear** se omite `id`; para **modificar** se incluye el `id` existente. Máx. **100 fixed prices por habitación**. Respuesta 201.
- **Campos que enviaremos** (subset del schema `fixedPrice`): `offerId` (oferta designada), `roomId`, `propertyId`, `firstNight`, `lastNight`, `name`, `roomPrice` + `roomPriceEnable=true`, y `minNights` si el host fijó estancia mínima. `strategy="default"`.
- **Rationale**: es el único endpoint que liga precio + rango de fechas + `offerId`; ya usamos el mismo adaptador y token (scope inventory read+write) para precios de calendario.
- **Alternativas**: `POST /inventory/rooms/calendar` (mueve el precio **base** por día, no una oferta con nombre/condiciones) — no sirve para "promoción sobre una oferta". Descartada para esta feature (sigue siendo el mecanismo de precios base de features previas).

## D2 — Retirada sin DELETE (decisión de clarify: "anular efecto + ocultar")

- **Hecho verificado**: el spec **no expone DELETE** de fixed prices (solo `GET` y `POST`).
- **Decisión**: "retirar" = **neutralizar** el fixed price vía `POST` (modify con su `id`) poniendo **`roomPriceEnable=false`** (el precio de la promo deja de aplicar) — con *fallback* a fijar `roomPrice` ≥ base si el canal ignorara el flag — y marcar la promoción como `retired` en nuestra BD para **ocultarla** de las activas. Efecto inmediato y reversible (re-habilitar).
- **Rationale**: cumple la intención del host (deja de descontar) sin borrar el registro que la API no permite borrar; reversible y auditable. Un registro neutralizado puede permanecer en el panel del canal hasta una limpieza manual eventual → se documenta en quickstart/operations.
- **Alternativas**: mover fechas al pasado (deja residuo confuso) o solo marcar en la app sin tocar el canal (no cumple: el descuento seguiría vivo). Descartadas.

## D3 — Oferta designada (decisión de clarify: "una oferta designada")

- **Decisión**: una sola **oferta designada** por configuración `beds24_promo_offer_id` (entero, 1–16) actúa de contenedor de todas las promociones v1. La app **lee** las ofertas (`GET /inventory/rooms/offers`) solo para validar que la designada existe y está publicable; **no** crea ni edita el contenedor (solo lectura por API — verificado: `/inventory/rooms/offers` no tiene POST).
- **Requisito operativo**: la oferta designada debe estar en `enable=always` (pública) para que la promo la vea el huésped; una oferta `internal` no se muestra públicamente. Se documenta como precondición (setup único en el dashboard).
- **Rationale**: YAGNI (Principio V) — evita un selector de ofertas y su UX; una designación por config basta para single-tenant.
- **Alternativas**: elegir entre ofertas existentes en cada creación (más flexible, más UX y estado) — diferido a una posible v2.

## D4 — Descuento: guardar % y precio absoluto (decisión de clarify)

- **Hecho verificado**: el schema `fixedPrice` **no tiene campo de porcentaje**; el precio es absoluto (`roomPrice`).
- **Decisión**: el host puede pedir % o precio; el sistema calcula `roomPrice = round(base * (1 - pct/100))` (redondeo a la moneda, COP sin decimales), **guarda ambos** (`discount_pct` y `price`), y envía el **precio absoluto**. El precio queda **fijado al crear** (no se recomputa si cambia el base); si el base cambia, la lista lo señala.
- **Redondeo**: COP se redondea a entero (a un múltiplo "bonito" p. ej. mil más cercano — a confirmar en implement con una regla simple `round(-3)` opcional). Nunca produce precio ≤ 0.
- **Rationale**: permite mostrar "20% off" y el ahorro sin depender de recomputar contra un base cambiante; coherente con FR-002.

## D5 — Precio base de referencia

- **Decisión**: el "precio base" para calcular el % y el ahorro se obtiene del **calendario** (precio `price1`/base del rango) vía el adaptador (ya tenemos `get_rates`). Si el rango tiene precios distintos por día, se usa una referencia representativa (el del primer día del rango) y se documenta; el descuento se aplica como un precio fijo de promo para todo el rango (una fixed price cubre firstNight..lastNight con un `roomPrice` único).
- **Rationale**: una fixed price es un precio único por rango; casa con cómo el canal modela la oferta.

## D6 — Validaciones y solape

- **Decisión**: rechazar `price ≤ 0`, `price ≥ base` (no es descuento), `pct ∉ (0,100)`, rango inválido/pasado (reutiliza validación de fechas de features 003/008). **Solape**: como guardamos las promociones en BD, detectamos solapes por (oferta, rango de fechas) y **advertimos pidiendo confirmación** antes de continuar (FR-011). Noches reservadas dentro del rango: se informa que las reservas confirmadas no cambian de precio (la promo afecta nuevas reservas).
- **Rationale**: cumple FR-005/FR-011; reutiliza utilidades existentes.

## D7 — Reconciliación / lectura

- **Decisión**: `GET /inventory/fixedPrices?propertyId&roomId` devuelve la lista (con `id`, `offerId`, fechas, precios). Guardamos el `external_id` (el `id` de Beds24) al crear, para poder **modificar/neutralizar** después. `list_promotions` combina nuestra BD (fuente de verdad de metadatos: %, estado, auditoría) con una verificación opcional contra el canal para el estado de publicación.
- **Rationale**: necesitamos el `id` externo para editar/retirar; la BD guarda lo que el canal no (el % pedido, el origen, la auditoría).

## D8 — Verificación de escritura acotada (Principio de seguridad + spec Assumption)

- **Decisión**: la validación de escritura real se hará en `implement` de forma controlada y **reversible**: crear una fixed price de prueba en la **oferta designada** con fechas lejanas y un descuento pequeño, verificar por `GET`, e inmediatamente **neutralizarla** (roomPriceEnable=false). Con confirmación explícita del host, dado que toca el listado real y no hay DELETE (limpieza final en dashboard si se desea).
- **Rationale**: cumple la regla de acciones que afectan sistemas externos; nada queda descontando tras la prueba.

## D9 — ADR

- **Decisión**: añadir `docs/adr/0003-api-promotions.md` documentando el hallazgo (V2 sí escribe fixedPrices/offers), la corrección a la conclusión de la Feature 009, y las decisiones D1–D8.
- **Rationale**: Principio I (decisiones de arquitectura como ADR).
