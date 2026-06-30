# Quickstart — Ofertas de Booking.com (v1 ligera)

## Por chat
- "crea una promoción que se VEA en Booking" / "pon un Early Booker visible" → el agente
  explica que esos deals se gestionan en Beds24/Booking y da el enlace; NO crea una promoción
  de precio interna.
- "baja el precio 10% en septiembre" → propone una promoción de precio interna (como hoy).
- "ponme una promo" (ambiguo) → el agente pregunta cuál de las dos.

## Sección "Ofertas" (web)
- En el menú lateral aparece "Ofertas".
- La página explica la distinción (Ofertas de Booking vs Promociones de precio internas) y
  ofrece enlaces al dashboard de Beds24 y al extranet de Booking, con un mini-instructivo.

## Verificación
- `GET`/navegación: la página `/offers` carga y los enlaces abren el destino correcto.
- Agente: las dos solicitudes anteriores se enrutan a la funcionalidad correcta (verificado por
  test y en vivo vía el proxy con cookie de sesión).
