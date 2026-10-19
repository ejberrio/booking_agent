# Feature Specification: Piloto interno de precios de la competencia (PriceLabs + Apify)

**Branch**: `037-market-pilot` · **Created**: 2026-10-19 · **Input**: issue #148. Decisión del anfitrión: "ambos en paralelo".
Documentos: `docs/research/piloto-mercado-decodo-apify.md` y `docs/research/legal-datos-mercado-2026-10.md` (fuera del repo público).

## Alcance
- **PriceLabs Market Dashboard** (licenciado, prueba de 30 días): el anfitrión lo conecta por Beds24 con la sincronización **apagada**; zona de Sabaneta/Mayorca, radio de 1,5–2 km, 2 a 4 habitaciones.
- **Apify** (actor público `tri_angle/new-fast-airbnb-scraper`, USD 0,0025 por anuncio; crédito gratis de USD 5): script **interno** `scripts/market_pilot.py`.
  - Para la zona del apartamento (y opcionalmente Cartagena) y 6 ventanas de 2 noches (fin de semana, entre semana, 4–6 dic, +30, +60 y el puente del 13–15 nov).
  - Calcula **solo agregados**: n, mediana, p25, p75 y percentil del precio propio.
  - Se compara contra PriceLabs y contra 10 anuncios que el anfitrión revisa a mano.

## Controles (memorando legal)
- Nada se guarda en la base de datos. A disco, fuera del repo, solo van los agregados y hasta 10 enlaces por zona para la verificación manual; se borran al terminar.
- Sin login ni cuentas de anfitriones, y sin configurar desbloqueadores.
- Gasto tope por corrida (`maxTotalChargeUsd`, `maxItems`).
- El token vive en el almacén de secretos (`apify_api_token`, alcance plataforma); lo pega el anfitrión y no se imprime.
- **No se muestra a clientes.**

## Tasks
- [x] T001 Secreto `apify_api_token` (API + etiquetas es/en/pt en Ajustes)
- [x] T002 `apps/api/scripts/market_pilot.py`
- [ ] T003 Corridas (3 días) + verificación manual + comparación con PriceLabs
- [ ] T004 Informe de decisión (go/no-go) en `docs/research/`
