# Contrato: Comportamiento del agente ante deals de Booking

## Regla en el prompt
- Si el host pide una **promoción VISIBLE en Booking** (deal/badge: "que se vea", "oferta de
  última hora visible", "Early Booker", "Genius"…): el agente EXPLICA que esos deals se
  gestionan en Beds24/Booking (no por la app), indica dónde (dashboard Beds24 / extranet) y
  NO crea una promoción de precio interna por error.
- Si el host pide **bajar el precio** (sin badge): usa la promoción de precio interna
  (`propose_create_promotion`).
- Ante ambigüedad ("ponme una promo"): el agente pregunta cuál de las dos quiere.

## Verificación
- Test de comportamiento: mensaje "crea una promoción que se vea en Booking" →
  la respuesta deriva a Beds24/Booking y NO genera una `AgentAction` de promoción interna.
- "baja el precio 10% en septiembre" → propone una promoción de precio interna.
