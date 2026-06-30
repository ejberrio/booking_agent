# Contrato: Sección "Ofertas" (web)

Página informativa en el menú lateral (`/offers`). NO consume API de ofertas (no existe).

## Contenido
- **Explicación de la distinción**, clara y breve:
  - "Ofertas de Booking" (deals visibles con badge) → se crean/gestionan en Beds24/Booking.
  - "Promociones de precio internas" → bajan el precio publicado; se gestionan en esta app
    (chat o calendario). Enlace a esa funcionalidad.
- **Deep-links** (abren en pestaña nueva):
  - Dashboard de Beds24 → Channel Manager → Booking.com → Promotions.
  - Extranet de Booking (Promociones/Oportunidades).
- **Mini-instructivo** (pasos) para crear un deal en el dashboard de Beds24.
- Nota: los enlaces son configurables; no contienen secretos.

## Reglas
- No promete sincronización (deja claro que el deal se gestiona fuera).
- Accesible desde el menú lateral con un ítem "Ofertas".
- `npm run build` verde.
