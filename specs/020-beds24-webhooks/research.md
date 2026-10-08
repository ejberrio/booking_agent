# Research: Reservas en tiempo real (020)

Fuentes: wiki de Beds24 ([Setting/propertiesnotifyurl](https://wiki.beds24.com/index.php/Setting/propertiesnotifyurl), [Category:Webhooks](https://wiki.beds24.com/index.php/Category:Webhooks)), OpenAPI V2 (`https://api.beds24.com/v2/apiV2.yaml`, operación *Webhooks - bookings*) y el panel del host (Settings → Properties → Access → **Booking Webhook**: campos *Webhook Version*, *URL*, *Custom Header*, *Additional Data*), revisado en modo lectura el 2026-10-08.

## R1. ¿Qué envía Beds24 y cuándo?

- **Decision**: usar **Booking Webhook versión 2**.
- **Rationale**: V2 = `POST` con JSON `{timeStamp, booking{id, propertyId, roomId, status, arrival, departure, firstName, lastName, price, …, stripeToken…}, infoItems, invoiceItems, messages, retries}`. Se dispara al crear, al cambiar algo que afecta disponibilidad (estado, llegada, salida, habitación) y al cancelar; los mensajes se encolan (demora media ~1 min). Si la respuesta es ≥ 400 o no hay respuesta, **reintenta** más tarde. V1 es `GET` con `bookid`/`status` en la URL y el propio wiki advierte que `status` puede no reflejar el estado real.
- **Alternatives**: V1 (sin cuerpo, estado poco fiable); Inventory Webhooks (Marketplace, a nivel de habitación, sin datos de reserva).

## R2. ¿Cómo autenticar los avisos?

- **Decision**: cabecera propia `X-StayLever-Key: <clave>` configurada en el campo **Custom Header** del Booking Webhook; comparación en tiempo constante contra el secreto `beds24_webhook_key`.
- **Rationale**: Beds24 no firma los avisos; el Custom Header existe en el Booking Webhook del panel. En cabecera la clave no aparece en URLs ni en logs de acceso (Cloudflare/Railway/Next). Rotación inmediata vía secret_service (caché write-through).
- **Alternatives**: clave en la URL (query o path) → queda en logs de acceso de terceros; IP allowlist → Beds24 no publica rangos estables.

## R3. ¿Confiar en el cuerpo del aviso?

- **Decision**: NO. Del cuerpo solo se leen `booking.id`, `propertyId`, `arrival`, `departure` como **pista del rango**; el estado se obtiene re-sincronizando desde la API de Beds24 con `import_remote(rango)` (reservas de la propiedad + calendario del rango). El cuerpo jamás se persiste ni se registra.
- **Rationale**: (a) fuente de verdad única (FR-004); (b) idempotencia y orden resueltos por construcción (FR-008/009); (c) una clave filtrada solo provocaría re-sincronizaciones, no datos falsos; (d) el cuerpo trae PII y tokens de pago (`stripeToken`, `pcibookingToken`) que no deben tocar disco ni logs.
- **Rango**: `[min(arrival, check_in previo), max(departure, check_out previo)]` para liberar también las noches viejas si cambiaron las fechas; sin fechas en el aviso → hoy..+90 (respuesta rápida; el cron diario cubre el año).
- **Alternatives**: aplicar el cuerpo directamente → duplicaría la lógica de import, aceptaría datos no verificados y obligaría a manejar orden/versiones.

## R4. Clave: ¿quién la genera?

- **Decision**: la app la genera (`secrets.token_urlsafe(32)`), la guarda cifrada (secret_service) y la devuelve **una sola vez** como línea lista para pegar (`X-StayLever-Key: …`); luego solo se ve la pista de 4 caracteres. Generar otra = rotar.
- **Rationale**: el host no técnico no tiene que inventar ni copiar una clave en dos lugares; es el patrón estándar de "API key mostrada una vez". Excepción acotada al principio write-only de 017: solo en la respuesta del generador, nunca recuperable después, no registrada (el middleware solo registra método/ruta/estado).
- **Alternatives**: el host inventa la clave y la pega en Secretos y en Beds24 (más fricción y claves débiles).

## R5. Respuesta y tiempos

- **Decision**: procesamiento en línea (rango corto: 1 calendario + 1 reservas, ~1–3 s); `200` aceptado (aunque el re-sync falle → `failed`, el cron corrige), `401` clave ausente/incorrecta, `503` sin clave configurada, `413` cuerpo > 256 KB (en la web).
- **Rationale**: devolver ≥ 400 ante un fallo de Beds24 provocaría reintentos contra el mismo Beds24 caído; mejor registrar y dejar que el cron repare. Sin colas (Principio V).

## R6. Entrada pública

- **Decision**: route handler de Next `POST /api/hooks/beds24` (público en el middleware, antes del chequeo de sesión) que reenvía cuerpo + `X-StayLever-Key` a `API_INTERNAL_URL/hooks/beds24`; sin logs propios.
- **Rationale**: la API sigue privada (solo la web es pública); patrón del proxy existente pero sin sesión y con una sola ruta y método.
