# Research: Feature 018 — Motor de sugerencias v2

**Date**: 2026-07-04 · Método: OpenAPI oficial de Beds24 + búsqueda web (proveedores de mercado) + lectura del código.

## R1. Ubicación de la propiedad (FR-003)

- **Hallazgo (apiV2.yaml oficial)**: el schema `property` de GET /properties incluye `address`, `city`, `state`, `latitude`, `longitude` — ya viajan en el import actual (no se persisten).
- **Decision**: `RemoteProperty` gana address/latitude/longitude; columnas nullable en `property`; `_upsert_property` las guarda/corrige. Zona de búsqueda default = city + address; editable en scan_config.

## R2. Proveedores de mercado pagos (estrategia "Ambos" — investigación pedida por el issue)

- **AirDNA**: el [API](https://www.airdna.co/vacation-rental-data-api) (métricas de mercado, ADR, ocupación, pricing futuro) es **solo Enterprise con precio custom** — fuera del rango USD 20-50/mes; los [planes](https://www.airdna.co/pricing) individuales (~USD 15-40/mes por mercado) son dashboard sin API.
- **PriceLabs**: [precios](https://hello.pricelabs.co/plans/) **USD 9.99/listing/mes fuera de US/EU** (Colombia aplica) + Market Dashboard ~USD 9.99/mes; tiene [Customer API](https://help.pricelabs.co/portal/en/kb/articles/pricelabs-api) e [API de integración](https://hello.pricelabs.co/dynamic-pricing-api/) (USD 1/listing/mes el sync API). OJO honesto: PriceLabs es un MOTOR de pricing (solaparía con el nuestro) más que una fuente cruda de datos; su valor aquí sería la referencia de mercado de su dashboard/API.
- **Decision**: puerto `MarketDataProvider` neutro; adaptador gratis (Tavily) construido YA; adaptador pago NO se construye en esta feature (sin cuenta activa que lo valide — YAGNI honesto), pero el puerto + config `market_provider` quedan listos y el ADR 0006 documenta el candidato (PriceLabs ~USD 10-20/mes total) y por qué AirDNA API quedó descartado a este tamaño.

## R3. Proveedor gratis: mercado vía búsquedas dirigidas (FR-004)

- **Decision**: `TavilyMarketProvider.get_snapshot(zone, month)` — consultas tipo "precio por noche apartamento {zone} {mes año} airbnb booking" (N configurable), extracción de tarifas con el LLM (mismo patrón que extract_events), **mediana** + sample_size; persiste en `MarketReference` (source="tavily", occupancy_pct=None — honesto: la ocupación de la zona no es obtenible gratis de forma fiable, documentado). `sample_size < 3` ⇒ confianza baja en el racional.
- **Rationale**: reutiliza los puertos search/LLM existentes; la mediana resiste outliers; nunca inventa (0 muestras ⇒ sin señal de mercado).

## R4. Señales y precio (FR-002/FR-006, decisiones del host)

- **Alcistas** (se conservan): evento (por relevancia +15/30%), ocupación alta (+10%). **Bajistas nuevas**: hueco ≤14 días sin reserva/evento (descuento progresivo: más cerca ⇒ más descuento), valle sin eventos con mercado por debajo del propio. **Límites**: tope −15% por sugerencia; piso `min_price`; techo `max_price`; mercado como ancla (promedio ponderado cuando hay snapshot con muestras suficientes).
- **Agrupación**: rango del evento (una sugerencia); señales sin evento → días contiguos con la misma señal Y el mismo precio base (si el base cambia a mitad de rango, se corta — `suggested_price` es un absoluto único).
- **Racional estructurado**: `rationale = {text, factors: [{kind: event|occupancy|gap|market, label, pct, event?: {name, location, dates, source_url}}], market?: {adr, samples, source}}` — retrocompatible (v1 solo tiene text; la UI muestra factores si existen).

## R5. Supersede (FR-005) y migración de las ~130

- **Decision**: `SuggestionStatus` gana `superseded` (terminal). Al persistir una sugerencia de rango R: `UPDATE ... SET status=superseded WHERE status=proposed AND solapa(R)`. Housekeeping en cada scan: proposed con date_to < hoy → superseded. Equivalencia exacta (mismo rango+precio) → no se crea (dedup actual). PG: `ALTER TYPE ... ADD VALUE` requiere `op.get_context().autocommit_block()`.
- Las resueltas (applied/rejected) y las approved históricas no se tocan. La lista de pendientes ya filtra proposed+approved → las superseded desaparecen solas de la UI.

## R6. Configuración del scan (FR-007)

- **Decision**: tabla `scan_config` de fila única (zone override, queries_per_scan default 12, event_kinds CSV opcional) + CRUD de POIs (`point_of_interest`: name, note distancia, date_from/date_to nullable, is_active). Query builder: zona + POIs activos (con sus fechas clave si las tienen) + tipos de evento. El IntelligenceRun.detail reporta consultas usadas / si el presupuesto quedó corto.
- Semilla (host): "Daviarena" (nota "muy cerca del apartamento", fechas 2026-09-01→2026-11-30 por la inauguración) y "CC Mayorca" (nota "al frente del apartamento").

Sources: [AirDNA API](https://www.airdna.co/vacation-rental-data-api) · [AirDNA pricing](https://www.airdna.co/pricing) · [PriceLabs plans](https://hello.pricelabs.co/plans/) · [PriceLabs Customer API](https://help.pricelabs.co/portal/en/kb/articles/pricelabs-api) · [PriceLabs Dynamic Pricing API](https://hello.pricelabs.co/dynamic-pricing-api/)
