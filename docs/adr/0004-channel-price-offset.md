# ADR 0004: Offset de precio por canal como multiplier componible del Channel Manager

**Fecha**: 2026-07-02 · **Estado**: aceptada · **Feature**: 013-channel-pricing (issue #88)

## Contexto

El calendario de Beds24 es UNO para todos los canales: la app no puede publicar precios
distintos por canal por la vía normal. Sin embargo, el mapping de cada canal en Beds24
admite un **multiplier** (fórmula string, p. ej. `*[CONVERT:COP-USD]` que hoy convierte
la moneda para Airbnb). El host necesita un ajuste porcentual por canal (p. ej. Airbnb
+8% para compensar el margen cambiario) gestionado desde la app con human-in-the-loop.

## Decisión

Materializar el offset como **factor multiplicativo añadido al multiplier del canal**
vía `POST /channels/settings` (API V2, estado Alpha):

- El multiplier se trata como `prefijo_del_operador` + `*factor_nuestro?`. El prefijo
  (p. ej. `*[CONVERT:COP-USD]`) es INTOCABLE; nuestro factor es siempre el sufijo
  `*<número>` final. +8% ⇒ `*[CONVERT:COP-USD]*1.08`; quitar el offset restaura el
  prefijo exacto.
- El puerto es neutro: `get/set_channel_price_adjustment(channel, factor: Decimal)` y
  `supports_price_adjustment(channel)`; la fórmula propietaria vive solo en el adaptador.
- Por ser Alpha, toda escritura se verifica con re-GET; discrepancia ⇒ SyncIssue y el
  estado local (`Channel.price_offset_pct`) no se persiste.
- **Límite asumido**: `/channels/settings` solo soporta multiplier para `airbnb` (y
  vrbo). Booking.com no tiene multiplier por API ⇒ **Booking vende al precio base** y el
  sistema lo comunica honestamente (el ajuste relativo se logra moviendo el base o el
  offset de Airbnb).

## Alternativas consideradas

- **Slots de precio por canal** (daily prices vinculados a price2..N en el mapping):
  duplica la escritura de calendario, requiere reconfigurar mappings en el dashboard y
  añade estado distribuido — rechazada (Principio V).
- **Editar el multiplier a mano en el dashboard**: es el statu quo; sin preview,
  auditoría, reversibilidad ni agente — justamente el problema a resolver.
- **Modelar la conversión de moneda en el dominio**: el CONVERT es neutro en valor y
  responsabilidad del operador/CM; el dominio solo habla en % — rechazada.

## Consecuencias

- 0 migraciones (se activa `Channel.price_offset_pct`, dormido desde la feature 001).
- El precio efectivo mostrado = `base × (1 + pct/100)` (COP); la conversión de moneda
  del canal no altera el valor y se anota en la UI.
- Una promoción (fixed price) en Airbnb recibe ADEMÁS el offset del canal
  (`allowMultiplier` default) — coherente: el offset es del canal, no del precio.
- Riesgo Alpha: el contrato del endpoint puede cambiar; mitigado con verificación
  post-write, SyncIssue y pruebas de contrato en el adaptador.
