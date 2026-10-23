# Feature 042: rentabilidad mensual (renta corta frente a arriendo tradicional)

**Rama:** `042-profitability` · **Depende de:** 026 (cuentas), 029 (modo sin conexión), sincronización con Beds24

## Por qué
El anfitrión necesita decidir, con sus propios números, si la renta corta le deja más que un
arriendo tradicional, una vez restadas comisiones, aseo y costos fijos. Hasta ahora StayLever no
guardaba el valor de las reservas.

## Qué
- **FR-001 Valor de cada reserva:** la sincronización con Beds24 V2 guarda, por reserva:
  - `price` → `amount` y `commission` → `commission`;
  - la moneda, deducida de `rateDescription` (Airbnb vía Beds24 puede venir en USD).

  Además trae **un año hacia atrás** (`arrivalFrom` = hoy − 400 días), en una sola consulta. Cambiar el valor no genera avisos.
- **FR-002 TRM:** la corrida diaria guarda en `fx_rate` la TRM oficial (datos.gov.co, conjunto
  `32sa-8pi3`, sin clave) de los días de llegada de las reservas en USD. Es una consulta por corrida y el informe nunca llama a la red.
- **FR-003 Tus números** (por unidad, `unit_finance`):
  - arriendo tradicional de referencia al mes;
  - costos fijos al mes (lo que pagaría el inquilino);
  - aseo por estancia.
- **FR-004 Informe** (`GET /profitability?unit_type_id=`), con 12 meses cerrados, el mes en curso y 3 meses reservados. Por mes:
  - noches y ocupación;
  - ingreso y comisiones, prorrateados por noche (lo que cruza de mes se reparte);
  - aseo en el mes de llegada y costos fijos;
  - neto, y diferencia contra el arriendo.
- **FR-005 Estimados:** una reserva sin valor del canal (modo sin conexión o reservas viejas) se
  calcula con el precio del calendario y una comisión típica (Airbnb 15,5 %, Booking 15 %, directa 0). El mes queda marcado «estimado».
- **FR-006 Resumen:** neto promedio al mes, diferencia contra el arriendo, ocupación y **noches al mes para igualar el arriendo** (con el neto por noche observado).
- **FR-007 Privacidad:** el informe nunca incluye nombres de huéspedes. Los datos son de la cuenta (aislamiento, principio VI).

## Datos
Migración `333969cbeb8c`:
- `booking.amount`, `booking.commission`, `booking.currency` (opcionales);
- tablas `unit_finance` (de la cuenta) y `fx_rate` (de la plataforma).

Volver a la versión anterior es seguro.

> Nota: la 041 (en pausa) tiene la migración `e1f2a3b4c5d7` sobre `d0e1f2a3b4c6`. Si se retoma, hay que rebasarla sobre esta.

## Web
Página «Rentabilidad», en la navegación, en es/en/pt:
- indicadores del resumen;
- formulario de «Tus números»;
- barras de neto por mes con la línea del arriendo;
- tabla mensual.

## Fuera de alcance
- Impuestos y depreciación de muebles.
- Ingresos de media estancia o por habitaciones: se evalúan aparte.
- Ocupación del mercado por mes (#185).
