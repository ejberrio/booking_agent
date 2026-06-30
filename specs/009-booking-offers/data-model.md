# Data Model — Ofertas de Booking.com (v1 ligera)

**Sin entidades persistentes nuevas.** v1 es informativa/guía: no se sincronizan ni
almacenan deals de Booking (la API del Channel Manager no los expone).

## Configuración (no ORM)

| Elemento | Descripción | Dónde |
|----------|-------------|-------|
| Enlace dashboard Beds24 (promociones Booking) | URL al panel donde se crean los deals | constante/config en la web |
| Enlace extranet de Booking | URL al extranet (Promociones/Oportunidades) | constante/config en la web |

> Si en el futuro se quisiera un "registro local" de deals (apunte manual para mostrar un
> indicador en el calendario), eso introduciría una entidad nueva; queda **fuera de v1**.

## Distinción (glosario, para UI y agente)

- **Oferta de Booking**: deal visible en el listing (badge/descuento). Se gestiona en
  Beds24/Booking, NO por la app.
- **Promoción de precio interna** (existente): baja el precio publicado; el huésped ve un
  precio menor sin badge. Se gestiona por la app (chat/calendario).
