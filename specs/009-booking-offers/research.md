# Research & Decisiones — Ofertas de Booking.com

## Hallazgo decisivo: la API de Beds24 V2 NO gestiona las promociones de Booking.com

Verificado en vivo contra la API V2 (token real, scopes `all:inventory`, `all:channels`,
`all:bookings-financial`, `all:properties` — sin limitación de permisos):

- `GET /promotions` → 404 "Invalid URI element".
- `GET /channels/booking`, `GET /channels/booking/promotions` → `null` (no es un recurso real).
- `GET /inventory/offers` / `inventory/rooms/offers` → exigen `arrival`; son **búsqueda de
  disponibilidad/tarifas** (qué ofertas hay para unas fechas), NO los "deals" visibles.
- Confirmado por la documentación: *"Promotions on Booking.com can now be created and managed
  directly in Beds24"* (dashboard) y *"mapping to booking.com cannot be done via the API"*.

**Conclusión**: crear/editar/listar las promociones NATIVAS de Booking (Basic Deal, Last-Minute,
Early Booker, Genius…) **no es posible por la API de Beds24 V2**. Se gestionan en el **dashboard
de Beds24** (Channel Manager → Booking.com → Promotions) o en el **extranet de Booking**.

- **Decisión**: NO construir creación/edición/listado por API (no existe). Activar el **Plan B**
  decidido en clarify: **guía + enlace profundo (deep-link)** a donde el host realmente gestiona
  los deals, y **claridad del agente** para no confundirlos con las promociones de precio internas.
- **Alternativas descartadas**: (a) crear por API → imposible; (b) leer por API → no expuesto;
  (c) usar `/inventory/offers` → es otra cosa (búsqueda), no deals.

## Re-alcance de v1 (lo realmente construible y valioso)

1. **Claridad del agente (núcleo del valor)**: cuando el host pida "una promoción que se VEA en
   Booking", el agente explica que esos deals se gestionan en Beds24/Booking (no por la app),
   da el enlace y NO crea una promoción de precio interna por error. A la inversa, si pide
   "bajar el precio", usa la promoción interna. Esto resuelve la confusión original.
2. **Sección "Ofertas" en la web (guía + accesos)**: explica la distinción (Ofertas de Booking
   visibles vs Promociones de precio internas) y ofrece **deep-links** al dashboard de Beds24 y
   al extranet de Booking para crear/editar los deals allí. Incluye un mini-instructivo.
3. **(Opcional, menor) Registro local de deals**: el host puede ANOTAR manualmente qué deals
   tiene activos (tipo, %, fechas) para que el calendario muestre un indicador y el agente lo
   tenga en contexto. Es un apunte local (no sincronizado, puede desfasar) → candidato a diferir
   o marcar claramente como "registro manual".

## Implicación para la especificación

Varios requisitos de la spec asumían create/edit/list por API (FR-001..FR-005). Con el hallazgo:
- FR-001 (listar por API), FR-002/003/005 (crear/editar/finalizar y publicar por API) → **no
  realizables**; se sustituyen por **guía + deep-link** (FR-014, que era el Plan B).
- FR-008/FR-009 (distinción y enrutado correcto del agente) y FR-010 (indicador en calendario,
  si hay registro local) → **siguen siendo válidos y son el verdadero valor**.

> Por esto, antes de generar data-model/contracts/tasks conviene **confirmar el re-alcance con el
> host**: ¿construimos la versión "guía + deep-link + claridad del agente" (sin sync real), o se
> gestionan los deals directamente en el dashboard de Beds24 y posponemos cualquier desarrollo?
