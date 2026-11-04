# Feature 043: demanda baja comparada con la ocupación del mercado (issue #185)

**Rama:** `043-market-low-demand` · **Mejora de:** 039 (techo p75 con demanda baja)

## Por qué
La 039 consideraba «demanda baja» cuando la ocupación **propia** de los próximos 30 días era menor
al 30 %. Con una sola unidad esa señal es ruidosa: el apartamento puede estar vacío por el precio,
no porque el mes esté flojo. En diciembre, cuando la zona se llena (~68 %), bajar el techo al p75
deja plata sobre la mesa.

## Qué
- **FR-001 Ocupación típica por mes** (`market_occupancy`): por zona (ciudad principal del área) y habitaciones (0 = todas), el % promedio de ocupación de cada mes del año.
  - Fuente inicial: PriceLabs Market Research (histórico de Airbnb).
  - Datos de plataforma, solo agregados: **nunca IDs de anuncios**.
- **FR-002 Carga:** Administración → Mercado → «Ocupación típica por mes», con 12 casillas (vacío = sin dato).
  - `POST /admin/market-occupancy` `{city, bedrooms, months: {1..12: %}}`.
  - `GET /admin/market-occupancy` devuelve el resumen.
- **FR-003 Regla:** si hay dato para el mes de la noche, la demanda baja exige además que la zona esté floja ese mes (**< 40 %**). Si el mes es fuerte, el techo sigue en el p90 aunque tu apartamento esté vacío. Sin dato del mercado, el comportamiento es igual al de la 039.
- **FR-004 Motivo:** «… — ocupación baja (la zona ronda el X % este mes): evento pequeño o mediano», en es/en/pt.

## Datos
Migración `0b5c228ff717`, que agrega la tabla `market_occupancy`. Volver a la versión anterior es seguro.

## Datos iniciales (Medellín/Sabaneta, 3 habitaciones; Market Research del 23-oct-2026, 237 anuncios)

| Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Sep | Oct | Nov | Dic |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 66,7 | 50 | 38,7 | 32,2 | 23,3 | 21,4 | 40,4 | 50 | 17 | 32,3 | 52,5 | 67,9 |

## Licencia
Igual que 038–040: uso interno como señal del motor (decisión del anfitrión, 21-oct-2026), pendiente de la respuesta de PriceLabs.
