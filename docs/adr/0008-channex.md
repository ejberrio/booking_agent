# ADR 0008 — Channex.io como channel manager marca blanca: todavía no

**Fecha**: 2026-10-23 · **Estado**: aceptado (revisar al cumplir los disparadores) · **Spike**: #153 (épica #158)

## Contexto

La Fase 2 comercial (#158) plantea que StayLever sea un "todo en uno": que el anfitrión conecte
Airbnb y Booking.com directamente con StayLever, sin pagar Beds24 aparte, usando Channex.io como
channel manager marca blanca. Hoy StayLever trabaja encima de Beds24, con el código de invitación
del anfitrión, y el anfitrión le paga a Beds24 unos €17 al mes.

Restricciones del negocio:
- clientes de 1–5 apartamentos;
- medio tiempo;
- costos fijos por debajo de US$100 al mes hasta tener ingresos;
- la API directa de Booking.com está cerrada a nuevos partners y Airbnb solo trabaja por invitación.

El spike (23-oct-2026) revisó precios, términos, la documentación técnica y la conexión con las
OTAs. Las fuentes están al final.

## Hallazgos

### Costos
Hay un solo plan, WhiteLabel, para "teams that build hotel software". No tiene setup, mínimo de
unidades ni cuota de certificación.

| Unidades (alquiler vacacional) | Solo channel manager | + mensajes y reseñas |
|---|---|---|
| 5 | US$132,50/mes | US$135/mes |
| 30 | US$145/mes | US$160/mes |
| 100 | US$180/mes | US$230/mes |

- La cuota de plataforma es de **US$130/mes y se cobra desde la primera propiedad con un canal activo**.
- Por unidad: US$0,50 al mes para alquiler vacacional (US$7 por propiedad si se clasifica como hotel).
- El cobro es mensual por adelantado. Precios sin IVA y en la moneda que fije el pedido (por confirmar).
- **Supera el presupuesto actual hasta tener ~25–30 unidades pagando.**

### Condiciones (Customer Agreement, actualizado al 30-sep-2026)
- **Solo para PMS o motores de reservas.** No aceptan revendedores puros: "require all partners to
  have a PMS system". Prohíben revender la cuenta, pero permiten integrarla en un producto propio
  con marca propia, sin mostrar "Powered by".
- **Certificación obligatoria** para obtener credenciales de producción:
  - 14 escenarios de prueba desde la interfaz del PMS (no desde Postman);
  - revisión en vivo por pantalla compartida;
  - no se acepta un full sync periódico, solo cambios, con cola y reintentos;
  - plazo no publicado.
- **Responsabilidad:**
  - StayLever da el soporte de primera línea y Channex el de segunda (cl. 8.2).
  - No hay cláusula de sobreventas: Channex excluye fallas de terceros y lucro cesante (cl. 18–19).
  - El tope de responsabilidad son las cuotas de 3 meses.
  - **El riesgo de sobreventa queda en StayLever y el anfitrión.**
- **SLA y salida:**
  - SLA del 99,5 % mensual, sin créditos: si no se cumple, el único remedio es terminar el contrato.
  - Se puede terminar con 30 días de aviso.
  - Exportación de datos hasta 30 días después; ley de Inglaterra y Gales.
- **Empresa:** Channex.io LTD (Gales, constituida en 2014; producto desde 2020).
  - Escala declarada: 456+ PMS, 65.000+ unidades VR.
  - Equipo pequeño y sin inversión pública.
  - En 2026 sus incidentes fueron casi todos caídas de Booking.com, incluida la del 22-oct.

### Técnica
- **Lo bueno:**
  - API completa para precios, disponibilidad, estancia mínima, CTA/CTD y stop-sell, con 500 días de horizonte.
  - Conexión de Airbnb por OAuth desde nuestra propia pantalla (`/meta/airbnb/connection_link`).
  - Iframe de canales en español (`lng=es`).
  - Webhooks firmados con HMAC y COP como moneda soportada.
  - Staging gratis, con propiedades de prueba de Booking.com.
- **Lo que pesa:**
  - StayLever pasa a ser la **fuente de verdad del inventario**. Eso exige:
    - feed de reservas con *ack*;
    - poll de respaldo cada 15–30 min, además de los webhooks;
    - volver a publicar la disponibilidad tras cancelaciones (el autoajuste viene apagado);
    - límite de 10 actualizaciones por minuto por propiedad, cola y backoff.
  - Booking.com requiere que el dueño acepte a Channex en su Extranet, con verificación en dos
    pasos. Ese paso no se puede embeber.
  - Promociones:
    - no hay API de promociones de Booking.com;
    - las de Airbnb fueron marcadas como obsoletas el 26-oct-2026;
    - hoy usamos promociones de Beds24 (ADR 0003), así que habría que simularlas con precio diario o tarifas derivadas.
  - No hay SDK de Python: el cliente se generaría desde la OpenAPI 3.1 pública.
  - Retención en Channex: las reservas se borran 6 meses después del checkout. Los datos del huésped hay que guardarlos de nuestro lado (Ley 1581, ver ADR 0007 y feature 028).

### Migración desde Beds24
- **Airbnb:** admite un solo PMS por cuenta y no admite co-anfitriones. Al desconectar Beds24 los
  anuncios pasan a manual hasta conectar Channex. "Unavailable by default" es incompatible.
- **Booking.com:** un proveedor de conectividad por propiedad. Las fuentes no coinciden en si hay
  que desconectar antes o si el cambio es continuo; hay que validarlo en un Extranet real.
- **Reservas existentes:** se importan con "Pull Future Bookings", sin datos personales y **sin
  descontar disponibilidad**. Hay que conciliar las reservas y los bloqueos antes de abrir el inventario.

### Alternativas
- **Beds24 Reseller:** marca propia con un mínimo mensual no publicado y sin certificación. Es la opción a cotizar en #151.
- **NextPax:** US$4 por unidad con un mínimo de US$350 al mes; no sirve a esta escala.
- **Rentals United:** tiene oferta de marca blanca, sin precios públicos.
- **Hostaway, Hospitable y Smoobu:** no encontré oferta de marca blanca.

## Decisión

1. **No integrar Channex todavía.** StayLever sigue encima de Beds24 con código de invitación en
   la Fase 1 (#150, #157). El costo fijo de Channex (US$130/mes) y la certificación no se
   justifican sin anfitriones pagando.
2. **Mantener la capa de canales como adaptador por cuenta** (`app/channels/base.py`). Cualquier
   operación nueva se diseña pensando en Channex: inventario propio, reservas idempotentes con
   ack y promociones como precio diario.
3. **Disparadores para retomar** (#154, #155). Hacen falta los tres:
   - ~25–30 unidades pagando, o un anfitrión grande que lo exija;
   - StayLever con módulo de reservas y disponibilidad propio (#155), porque es requisito para certificar;
   - Beds24 Reseller (#151) descartado o más caro.
4. **Mientras tanto, sin costo:**
   - preguntar a Channex por escrito: si un asistente de precios con reservas cuenta como PMS, moneda e IVA para Colombia, plazo de certificación y algún descuento mientras no haya unidades activas;
   - cotizar Beds24 Reseller (#151).

## Plan de integración (cuando se cumplan los disparadores)
1. Cuenta de staging. El anfitrión crea la cuenta; la clave va en Ajustes → Secretos.
2. `ChannexAdapter` con cliente httpx generado desde la OpenAPI:
   - cola o outbox por propiedad, con backoff ante 429 y 5xx;
   - revisar siempre `meta.warnings`;
   - precios como decimal en texto.
3. Reservas: webhook firmado, poll del feed cada 15 min con un lock compartido, ack después de guardar, y conciliación diaria.
4. Conexión: Airbnb por OAuth embebido; Booking.com con una guía paso a paso del Extranet; iframe `lng=es` para el mapeo.
5. Los 14 escenarios de certificación desde la interfaz de StayLever, y luego la revisión en vivo.
6. Migración piloto con el apartamento del anfitrión: conciliar, desconectar Beds24 en horario de baja demanda, conectar, *Pull Future Bookings*, full sync, verificar en cada OTA y solo entonces cancelar Beds24.

## Consecuencias
- No se agregan costos fijos ni riesgo de sobreventas mientras se valida el producto.
- El anfitrión sigue pagando Beds24, que es una fricción comercial; se mitiga con el código de invitación (#150).
- Si Beds24 Reseller resulta viable y barato, puede reemplazar a Channex como camino de marca blanca. Se decide en un ADR nuevo.

## Fuentes
- Precios y términos: https://channex.io/pricing · https://channex.io/policy · https://docs.channex.io/about-channex-and-faq
- Certificación y técnica: https://docs.channex.io/api-v.1-documentation/pms-certification-tests · https://docs.channex.io/api-v.1-documentation/rate-limits · https://openapi.channex.io/public/openapi.json · https://docs.channex.io/guides/channex-retention-periods · https://docs.channex.io/changelog
- Canales: https://docs.channex.io/channel-mapping-guides/airbnb · https://docs.channex.io/channel-mapping-guides/booking.com · https://docs.channex.io/api-v.1-documentation/channel-iframe · https://www.airbnb.com/help/article/2958
- Alternativas: https://beds24.com/reseller.html · https://nextpax.com/nextpax-pricing
- Estado: https://status.channex.io/ · Companies House 09250795
