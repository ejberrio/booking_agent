# Feature 040: cargar el CSV de PriceLabs desde Administración

**Rama:** `040-market-csv-upload` · **Depende de:** 038 (techo p90) y 039 (techo p75 con demanda baja) · **Issue:** seguimiento de #148

## Por qué
Los percentiles de mercado (`market_band`) solo se podían cargar con un script. Los precios
publicados cambian cada día y el techo pierde valor si no se refresca. La carga debe poder
hacerla el administrador de plataforma en ~3 minutos por zona, sin tocar código.

## Qué
- **FR-001 Carga del CSV:** en Administración → «Mercado (PriceLabs)»:
  - se elige el municipio de la zona (se guarda en la ciudad principal del área: Sabaneta → Medellín);
  - se eligen las habitaciones (0 = todas), que deben coincidir con el filtro usado en PriceLabs;
  - se sube el archivo de «Precios Futuros» → «Descargar CSV».
- **FR-002 Formato:** `Dates, 25th Percentile, 50th Percentile, 75th Percentile, 90th Percentile, Median Booked Price, No. Of Bookings`.
  - Las columnas se reconocen por nombre (también en español), así que el orden y las columnas extra no importan.
  - Se aceptan coma, punto y coma o tabulador.
  - Se guardan solo las fechas desde hoy y hasta 400 días; el historial que trae el CSV se ignora.
  - Se descartan las filas sin fecha, con percentiles vacíos o desordenados (p25 ≤ p50 ≤ p75 ≤ p90), y se informa cuántas.
  - Un archivo que no sea de «Precios Futuros» se rechaza con un mensaje claro.
- **FR-003 Reemplazo:** una nueva carga reemplaza las fechas existentes de esa zona y tamaño, sin duplicar, y conserva las demás.
- **FR-004 Resumen:** por zona y tamaño se muestran:
  - las fechas cubiertas desde hoy;
  - la mediana típica (p50 promedio);
  - la fecha de la última carga;
  - avisos «vieja: refréscala» (más de 35 días) y «se acaba pronto» (los datos terminan en menos de 60 días).
- **FR-005 Borrar:** se pueden borrar los datos de una zona y tamaño (p. ej. si se cargó el filtro equivocado), con confirmación.
- **FR-006 Seguridad:**
  - solo el administrador de plataforma puede usarlo;
  - los datos son agregados (percentiles), sin anuncios ni personas;
  - el CSV no se guarda: solo los percentiles.

## API
- `POST /admin/market-bands/csv` `{city, bedrooms, csv}` → `{imported, past, invalid, city, from, to, bands}`.
- `DELETE /admin/market-bands?city=&bedrooms=` → `{deleted, bands}`.
- `GET /admin/market-bands` → resumen desde hoy, con `p50_avg` y `updated_at`.

## Datos
- `market_band.updated_at`: columna opcional nueva (migración `d0e1f2a3b4c6`). Volver a la versión anterior es seguro.

## Fuera de alcance
- Descargar el CSV automáticamente desde PriceLabs (no hay API pública de Market Dashboard; se preguntó a soporte el 20-oct).
- Guardar «Median Booked Price» y el número de reservas.
- Recordatorio automático mensual por correo.

## Licencia
Uso interno como techo de sugerencias mientras PriceLabs confirma el alcance de la licencia (correo del 20-oct-2026).
