# ADR 0006 — Motor de sugerencias v2 y puerto de datos de mercado

**Fecha**: 2026-07-04 · **Estado**: aceptado · **Feature**: 018 (issue #98)

## Contexto

El motor v1 solo tenía señales alcistas (evento +15/30%, ocupación +10%), generaba una sugerencia
POR DÍA (acumuló ~130 pendientes con duplicados por fecha) y su racional era texto genérico sin
decir qué evento ni dónde. La referencia de mercado nunca operó (tabla vacía). Decisiones del host
(clarify 2026-07-04): agrupación por evento/rango; tope bajista −15%; POIs semilla Daviarena
(sep-nov 2026) + CC Mayorca; ventana de hueco 14 días.

## Decisión

1. **Señales simétricas**: alcistas conservadas + bajistas (hueco libre a ≤14 días con descuento
   progresivo — más cerca ⇒ mayor —, tope −15%, piso min_price y techo max_price SIEMPRE).
   La ocupación pasa de "día tomado" (v1, sin sentido: ese día no se puede vender) a densidad de
   la ventana ±7 días; las noches ocupadas quedan EXCLUIDAS de toda sugerencia.
2. **Agrupación por rango**: una sugerencia por (señal dominante × días contiguos × mismo precio
   base — se corta si el base cambia, porque suggested_price es un absoluto único). El flujo de
   resolución de la feature 014 no cambia (apply ya itera rangos).
3. **Supersede**: estado terminal nuevo `superseded`; al persistir un rango, las `proposed`
   solapadas se reemplazan; housekeeping de vencidas en cada corrida. El primer scan v2 depura
   lo acumulado. Resueltas (applied/rejected) y approved históricas: intactas.
4. **Racional estructurado retrocompatible**: `rationale = {text, factors[], market{}}` — cada
   factor con kind/label/±% y, si es evento, nombre/lugar/fechas/fuente. Las v1 (solo text)
   siguen renderizando.
5. **Puerto `MarketDataProvider`** (estrategia "Ambos" del host): `get_snapshot(zone, month) →
   MarketSnapshot | None`. Gratis (construido): búsquedas Tavily dirigidas + extracción LLM de
   tarifas → MEDIANA + sample_size; ancla el precio solo con ≥3 muestras (con menos, informa
   "confianza baja" sin anclar); 0 muestras → None (nunca se inventa). Ocupación de zona: None
   (no obtenible gratis de forma fiable — honesto).
6. **Proveedor pago (research)**: AirDNA API es SOLO Enterprise (precio custom, fuera de rango);
   el candidato realista es **PriceLabs** (~USD 9.99/listing/mes fuera de US/EU + Market Dashboard
   ~9.99; tiene API de cliente). NO se construye el adaptador sin una cuenta que lo valide (YAGNI
   honesto); el puerto y la configuración quedan listos para enchufarlo.
7. **Contexto**: la propiedad persiste address/lat/lon del CM (el schema de Beds24 los expone en
   GET /properties); POIs manuales (CRUD) + ScanConfig (zona, consultas por corrida, tipos)
   dirigen las consultas; el run reporta presupuesto usado.

## Consecuencias

- El scan diario consume ~10-15 créditos Tavily por corrida (config editable; free tier 1000/mes).
- Las ~130 sugerencias pendientes v1 quedarán `superseded` en el primer scan v2 (limpieza).
- Contratar PriceLabs es decisión futura del host; añadirlo será un adaptador nuevo del puerto.
