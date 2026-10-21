# Feature 041: percentiles de mercado por la API de PriceLabs (automático)

**Rama:** `041-pricelabs-api` (sobre 040) · **Depende de:** 038–040 · **Issue:** seguimiento de #148

## Por qué
La carga por CSV (040) es manual y se queda vieja. La Customer API de PriceLabs
(`GET /v1/neighborhood_data`) devuelve los mismos percentiles de «Precios Futuros» por fecha.
Así se pueden refrescar cada día sin intervención.

## Qué
- **FR-001 Clave:** secreto de plataforma `pricelabs_api_key`. Lo pega el anfitrión en Ajustes → Secretos; nunca aparece en logs, errores ni repositorio. Para tenerla: PriceLabs → Account Settings → API Details → Enable (USD 1 por anuncio al mes).
- **FR-002 Configuración por zona y tamaño:** en Administración → Mercado → «Automático (API de PriceLabs)»:
  - se listan los anuncios de la cuenta de PriceLabs (`GET /v1/listings`: id, pms, nombre, ciudad, habitaciones y si sincroniza);
  - se elige uno y se guarda para el municipio y las habitaciones de arriba;
  - al guardar se prueba de inmediato.
- **FR-003 Origen de los datos:** se elige EN PriceLabs, en ese anuncio: Neighborhood Data → Market Dashboard + compset (p. ej. 3 habitaciones).
  - StayLever no llama a `update_source` ni a ningún endpoint que escriba: solo `GET`.
- **FR-004 Lectura:** de `Future Percentile Prices` se toman las etiquetas 25th/50th/75th/90th Percentile.
  - Categoría: la del número de habitaciones (`"3"`); si hay una sola (compset del Market Dashboard), esa; con «todas», `All`.
  - Solo se guardan las fechas desde hoy, con `source = "pricelabs-api"`, en `market_band` (reemplaza por fecha).
- **FR-005 Corrida diaria:** `scan_daily` refresca todas las configuraciones activas antes de calcular sugerencias.
  - Sin configuración o sin clave no hace nada.
  - Un 401 detiene la corrida.
  - El fallo de una zona no detiene las demás.
- **FR-006 Estado visible:** por configuración se ven la última corrida, el resultado («ok: N fechas … · origen · categoría») o el error legible, y los botones «Probar ahora» y «Quitar» (los datos ya cargados se conservan).
- **FR-007 Errores legibles, sin secretos:** 401 clave, 404 anuncio, 429 límite, 400 con su motivo.
  - Si el motivo menciona *sync*, se avisa que PriceLabs pide «Sync Prices» encendido.

## Resultado de la prueba (21-oct-2026) — EN PAUSA
- **Customer API:** la clave es válida y `GET /v1/listings` funciona. `neighborhood_data` responde 400 «Listing sync is not toggled ON in PriceLabs».
- **Conector de IA (MCP), solo lectura:**
  - `get_listing_neighborhood_market` responde lo mismo (400).
  - `get_neighbourhood_data` responde 422 `ERR-MCP-LISTING-NOT-SYNCING`.
  - `market_research` responde 403 `ERR-MCP-FEATURE-NOT-ENABLED`: hay que pedir a soporte que lo activen (beta gratis, 20 consultas al día).
- **Conclusión:** sin encender Sync no hay percentiles por API. La rama queda sin pasar a producción y la fuente sigue siendo el CSV mensual (040).

## Riesgos abiertos
- **Sync Prices:** la documentación lista «sync off» como causa de 400 en `neighborhood_data`, y el cobro es por anuncio que sincroniza. Si se confirma que exige sincronizar, NO se enciende sin decisión del anfitrión: PriceLabs empezaría a cambiar los precios en Beds24.
- **Licencia:** los términos de PriceLabs (https://hello.pricelabs.co/tandc/) permiten el uso solo para el negocio propio, sin redistribuir. El anfitrión decidió el 21-oct-2026 seguir mientras responde soporte; si no lo permite, la fuente pasa a ser solo scraping.
- **Límites:** 60 peticiones/min y 1.000/hora; se usa 1 petición por zona y tamaño al día.

## Fuera de alcance
- Cambiar el origen (compset) desde StayLever (`update_source`).
- Ocupación futura del mercado (`Future Occ/New/Canc`): candidata para mejorar la señal de demanda baja (039).
