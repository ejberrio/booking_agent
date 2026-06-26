# Research — Motor de precios

Formato: Decisión / Justificación / Alternativas.

## 1. Qué precio se publica → el precio EFECTIVO

- **Decisión**: Se publica a Beds24 el **precio efectivo** del día (base − mejor promoción vigente), calculado con `effective_price`/`best_promotion` (dominio 001). Las promociones no se mapean a las nativas de Beds24.
- **Justificación**: Clarificación del host. Simple y siempre correcto: Booking ve el precio final que queremos cobrar.
- **Alternativas**: publicar base + promociones nativas de Beds24 (más fiel a la UX "% off" de Booking, pero más complejo y con soporte variable en V1) — descartado por ahora.

## 2. Recálculo y re-publicación al cambiar promociones

- **Decisión**: Crear/editar/eliminar una promoción dispara: (a) auditar el cambio de promoción, (b) recalcular el efectivo de los días afectados (intersección de la vigencia de la promo con los días que tienen precio), (c) re-publicar esos efectivos vía el conector.
- **Justificación**: Como publicamos efectivo (decisión 1), un cambio de promo cambia lo que se vende; debe llegar a Booking (FR-015).
- **Alternativas**: no re-publicar (dejaría Booking desincronizado) — descartado.

## 3. Previsualización (diff) y detección de obsolescencia

- **Decisión**: `preview_range` devuelve un objeto transitorio `ChangePreview` con, por día afectado, (valor anterior, valor nuevo, válido/ inválido + motivo) y una **huella (fingerprint)** = hash de los pares (día, precio_base_actual) afectados. `apply_range` recibe el `fingerprint` esperado; si al aplicar la huella recalculada difiere → **preview obsoleto**: no aplica, exige re-previsualizar.
- **Justificación**: Cumple human-in-the-loop (preview + confirmación) y evita aplicar sobre un estado cambiado (FR-004, FR-013). Sin persistir el preview.
- **Alternativas**: persistir el preview con TTL (más estado, innecesario a esta escala); aplicar sin huella (riesgo de pisar cambios) — descartado.

## 4. Días inválidos en operaciones de rango

- **Decisión**: Los días fuera de los límites min/max se marcan `inválido` en el preview y se **excluyen** de la aplicación; los válidos sí se aplican (clarificación).
- **Justificación**: No bloquear toda la operación por un día; mejor UX, el host ve qué quedó fuera.
- **Alternativas**: bloquear todo (todo-o-nada) — descartado por el host.

## 5. Auditoría de promociones → tabla `PromotionChangeLog`

- **Decisión**: Nueva tabla `promotion_change_log` con acción (created/updated/deleted), `before`/`after` (snapshot JSON), origen y timestamp. La auditoría de **precio base** sigue en `PriceChangeLog` (001).
- **Justificación**: El cambio de promoción no altera el precio base, así que no encaja en `PriceChangeLog`; una tabla dedicada da trazabilidad limpia (clarificación).
- **Alternativas**: forzar el evento en `PriceChangeLog` (semántica confusa) — descartado.

## 6. Publicación eficiente del efectivo (agrupación)

- **Decisión**: Al publicar varios días, agrupar días **contiguos con el mismo efectivo** en rangos y llamar `set_rate_range` por grupo (reduce llamadas y `SyncRun`). Días con precio distinto → grupos distintos.
- **Justificación**: Menos llamadas a la API y menos ruido de auditoría de sync; respeta verificación.
- **Alternativas**: una llamada por día (simple pero ruidoso) — válido como fallback.

## 7. Reutilización de 001/002 y publicación inyectable

- **Decisión**: La escritura de precio base usa `pricing_service.set_base_price` (auditada); el rollback usa `audit_service.rollback_change`. La publicación usa el puerto `ChannelManager` **inyectado** (Beds24 real en runtime, **falso en tests**). El cálculo del efectivo usa el dominio 001.
- **Justificación**: No reimplementar lógica; tests sin API real (principio IV).
- **Alternativas**: duplicar lógica de precios en esta capa — descartado (DRY).

## 8. Selección de rango

- **Decisión**: `RangeSelection` = (date_from, date_to) + filtro opcional `weekdays` (subconjunto de lun–dom) y/o lista explícita de días (`days`). Se expande a una lista de fechas concretas.
- **Justificación**: Cubre "semana/mes/rango arbitrario, solo viernes y sábados, grupos de días" (FR-003).
- **Alternativas**: solo rango contiguo (insuficiente para "fines de semana").

## Sin NEEDS CLARIFICATION pendientes

Las decisiones de negocio (días inválidos, precio efectivo, auditoría de promos) se resolvieron en `/speckit-clarify`.
