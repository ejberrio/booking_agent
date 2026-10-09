# Research: 023 Extender precios

## R1 — ¿Dónde está la verdad de "noche sin precio"?
- **Decisión**: la vista previa lee `GET inventory/rooms/calendar` (precio + numAvail) del CM desde hoy hasta la fecha final, en una sola llamada.
- **Por qué**: la sincronización local cubre 365 días y guardaba 0 para "sin precio". La lectura remota también resuelve el caso "publicado pero no verificado": la siguiente vista previa ya no lo propone.
- **Alternativas**: solo datos locales (no ve más allá de 365 días ni cambios hechos en Beds24).

## R2 — Hallazgo de producción (2026-10-08)
- Beds24: `price1` hasta 2027-02-12; desde 2027-02-13 sin `price1` y `numAvail 0`; 2027-05-01..03 `numAvail 1` sin precio. `GET inventory/rooms/offers` no devuelve ofertas para marzo, mayo ni junio de 2027.
- Beds24 no devuelve precios pasados → no existe el "mismo día del año anterior" para feb–jun.
- Precios locales: planos por mes (sin diferencia entre semana y fin de semana); oct 270 k, nov 370 k (picos de evento hasta 611 k), dic y ene 378 k.

## R3 — Plantilla propuesta
- **Decisión**: para cada año-mes objetivo, la mediana de los precios conocidos (> 0) del mismo mes del año (cualquier año), excluyendo las noches cubiertas por un `Event`. Sin datos de ese mes → mediana global sin eventos. Sin ningún dato → mínimo de la regla, o nada (el host debe escribirlo; la API lo rechaza si es ≤ 0). Redondeo al millar más cercano.
- **Por qué**: la mediana ignora los picos de evento; el host ajusta lo demás.

## R4 — Precio por noche y límites
- `p = round_1000(plantilla × (1 + fds/100))` si la noche es viernes o sábado, si no `round_1000(plantilla)`; después `clamp(p, mínimo, máximo)` marcando `clipped_min`/`clipped_max`. `fds` ∈ [0, 50].

## R5 — Disponibilidad
- Abrir si `numAvail remoto == 0`, `open_closed` está activo y la noche NO tiene `CalendarDay.is_blocked` local (bloqueo hecho por el host desde la app). Valor = `unit.units_count`.
- Bloqueada por el host → solo precio (`kept_closed`).
- Reserva confirmada → se omite. Noche con precio remoto > 0 → no es objetivo.

## R6 — Escritura y verificación
- **Puerto**: `set_calendar_entries(room, entries: list[CalendarEntry(date_from, date_to, price, num_avail | None)]) -> WriteResult`.
- **Beds24 V2**: un POST con todos los tramos del mes; después un GET del rango del mes para verificar precio y, si se envió, disponibilidad. V1 → `ChannelError`.
- Tramos dentro del mes = noches contiguas con igual (precio, abrir).

## R7 — Aplicación por mes
- `async with session.begin_nested()`: `set_base_price(origin=extension, validate_rule=False)` por noche, `CalendarDay` y `AvailabilityChangeLog(origin=extension)` para las que se abren, y publicación. Si falla (excepción o sin verificar) → excepción interna → rollback del mes, `SyncIssue(entity_ref="price-extension:YYYY-MM")` fuera del savepoint, mes `failed`.

## R8 — Huella
- sha256 de: fecha final, % fin de semana, abrir, precios e inclusión por mes, mínimo y máximo, y por noche objetivo `fecha:precio_remoto:numAvail:bloqueada:reservada`. Se recalcula al aplicar (vuelve a leer el CM).

## R9 — Estado del horizonte
- Local: primera fecha ≥ hoy sin `Rate > 0` (búsqueda hasta hoy + 730). `needs_extension = primera < hoy + 365`. `months_covered` = meses completos entre hoy y esa fecha. `default_until = hoy + 18 meses`, `max_until = hoy + 24 meses`.

## R10 — Precio 0
- `pricing_service.get_price` devuelve `None` si ≤ 0 (calendario, KPIs, motor y agente pasan por ahí o por la vista del calendario).
- `sync_service.import_remote`: no crea `Rate` con precio ≤ 0. Si el local es ≤ 0 y el remoto > 0, actualiza como baseline sin incidencia.
- Migración: borra `rate` con `base_price <= 0`.

## R11 — Costo en Beds24
- ~15 meses × (1 POST + 1 GET) + 1 GET de vista previa ≈ 31 llamadas por extensión: muy por debajo del límite de créditos de V2. Sin costo adicional del plan.
