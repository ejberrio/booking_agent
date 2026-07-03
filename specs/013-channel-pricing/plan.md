# Implementation Plan: Precios y promociones por canal (Booking.com + Airbnb)

**Branch**: `013-channel-pricing` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-channel-pricing/spec.md`

## Summary

Dar control y visibilidad del precio por canal. Investigación en vivo (research.md) resolvió las dos incógnitas: (R1) el ajuste por canal se materializa en el **multiplier del canal en Beds24** vía `POST /channels/settings` (Alpha; string componible — se preserva la fórmula `*[CONVERT:COP-USD]` existente y se añade `*factor`); soportado para **airbnb** (Booking no tiene multiplier → vende a precio base, y el sistema lo dice honestamente). (R2) los fixed prices **SÍ se limitan por canal** vía el campo `channels: {airbnb: {enable: bool}, ...}` (verificado en los 6 fixed prices reales de la cuenta). Diseño: puerto con dos métodos nuevos neutrales (`get/set_channel_price_adjustment` — el dominio habla en "factor decimal", la fórmula propietaria vive en el adaptador); servicio `channel_pricing_service` con preview→confirm→apply→audit (Principio III); `Promotion` gana alcance de canales (JSON `conditions`); auditoría del offset en tabla nueva `channel_offset_log` (única migración); agente con tool de lectura + propuesta de offset; web con tarjeta de ajustes en Configuración, alcance en Ofertas y deep-links de Airbnb. Default 0%/None ⇒ comportamiento actual intacto (FR-012).

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript/React 19 (web)
**Primary Dependencies**: FastAPI + SQLAlchemy 2.0 async (api); Next.js 15 + react-query + sonner (web)
**Storage**: PostgreSQL. `Channel.price_offset_pct` ya existe (Numeric(5,2), nullable); el alcance de promociones va en `Promotion.conditions` (JSON existente). **Una migración mínima**: tabla append-only `channel_offset_log` (la auditoría del offset necesita tabla propia: `AgentAction` exige conversation_id y solo cubre el chat — desviación documentada en implement, Principio I)
**Testing**: pytest + httpx.MockTransport (adaptador) + dobles del puerto (servicios); npm run build (web)
**Target Platform**: Railway (CD a main), Neon
**Project Type**: web application (monorepo apps/api + apps/web)
**Performance Goals**: sin cambios de complejidad; 1 llamada extra al CM solo al aplicar/consultar offsets (no en el hot path del calendario)
**Constraints**: `POST /channels/settings` es **Alpha** → escritura verificada con re-GET + SyncIssue en fallo (FR-011); multiplier de Airbnb contiene `*[CONVERT:COP-USD]` que NO puede romperse; offset acotado a [−50%, +100%]; 129 tests existentes intactos
**Scale/Scope**: 1 propiedad, 2 canales gestionados (booking/airbnb); ~13 archivos, 1 migración mínima (tabla de auditoría)

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ spec→plan→tasks→analyze→implement; decisión de mecanismo documentada en research.md + ADR 0004 (multiplier componible como materialización del offset) |
| II. Provider-agnostic | ✅ El puerto expone `get/set_channel_price_adjustment(channel_token, factor: Decimal)` — el dominio nunca ve la fórmula `*[CONVERT:...]*1.08` ni el endpoint Alpha; eso vive en `beds24_v2.py`. `RemoteFixedPrice.channels` usa tokens neutros |
| III. Human-in-the-loop (NO NEGOCIABLE) | ✅ Offset y alcance de promoción son ESCRITURAS: patrón preview(fingerprint)→confirm→apply→audit (ChannelOffsetLog con antes/después) y reversible (aplicar el valor anterior). El agente solo propone (`propose_channel_offset`) |
| IV. Tipado y pruebas | ✅ Tests de adaptador (composición del multiplier preservando prefijo, channels en el body de fixedPrices), servicio (validación de rango, honestidad canal no soportado, fingerprint), promos con alcance. Verificación en vivo acotada y reversible en quickstart |
| V. Simplicidad (YAGNI) | ✅ 1 migración mínima (solo la tabla de auditoría); el precio efectivo es cálculo derivado (no persistido); no se construye gestión de deals nativos ni per-day pricing por canal (slots) — el multiplier cubre el caso real |

**Post-diseño (re-check)**: sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/013-channel-pricing/
├── plan.md
├── research.md          # R1 multiplier vía /channels/settings · R2 fixedPrice.channels · hallazgos en vivo
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── channel-manager-port.md   # get/set_channel_price_adjustment + RemoteFixedPrice.channels
│   ├── pricing-api.md            # GET/POST /pricing/channel-offsets + scope en /pricing/promotions
│   └── agent-tools.md            # get_channel_offsets, propose_channel_offset, prompt
└── tasks.md
```

### Source Code (repository root)

```text
apps/api/
├── app/
│   ├── channels/
│   │   ├── base.py                 # += get/set_channel_price_adjustment; RemoteFixedPrice.channels
│   │   └── beds24_v2.py            # /channels/settings GET/POST (Alpha), composición del multiplier,
│   │                               #   channels {token: {"enable": bool}} en _fixed_price_body
│   ├── services/
│   │   ├── channel_pricing_service.py  # NUEVO: get/preview/apply offset (fingerprint, audit, SyncIssue)
│   │   └── offer_promotion_service.py  # alcance de canales en preview/apply/list (conditions JSON)
│   ├── agent/
│   │   ├── tools.py                # += get_channel_offsets (read), propose_channel_offset (write)
│   │   └── prompts.py              # regla de offsets ("menciona el efecto por canal")
│   └── api/routes/pricing.py       # += GET /pricing/channel-offsets, POST .../preview|apply;
│                                   #   channels_scope en promotions preview/apply
└── tests/
    ├── test_beds24_v2_channel_settings.py  # NUEVO: GET/POST multiplier (preserva prefijo), Alpha errors
    ├── test_channel_pricing_service.py     # NUEVO: rango, honestidad, fingerprint, audit, revert
    ├── test_offer_promotion_scope.py       # NUEVO: scope en body/preview/list; default = todos
    └── test_agent_channel_offsets.py       # NUEVO: tools + prompt

apps/web/
├── app/(app)/settings/page.tsx     # tarjeta "Precio por canal" (ver/editar offset con preview→confirmar)
├── app/(app)/offers/page.tsx       # selector de alcance + alcance en lista + deep-links Airbnb + guía 3 vías
├── lib/links.ts                    # += airbnbMulticalendar, beds24AirbnbPromotions
└── lib/{api.ts,types.ts}           # offsets + scope
```

**Structure Decision**: monorepo existente; un servicio nuevo (`channel_pricing_service`) y extensiones puntuales. Sin módulos web nuevos (se reutilizan Configuración y Ofertas).

## Diseño (decisiones clave)

1. **Materialización del offset (R1)**: factor = `1 + pct/100` (4 decimales). El adaptador lee el multiplier actual del canal, separa el **prefijo base** (todo lo que no sea un `*<número>` final) y escribe `prefijo + "*<factor>"` (u omite el sufijo si pct=0). Así `*[CONVERT:COP-USD]` + 8% ⇒ `*[CONVERT:COP-USD]*1.08`; y quitar el offset restaura el prefijo exacto. Verificación: re-GET tras el POST y comparación (endpoint Alpha, FR-011).
2. **Canales soportados**: capacidad declarada por el adaptador (`supports_price_adjustment(channel)` → beds24: solo `airbnb`). Para `booking` el servicio responde honesto: "Booking vende al precio base; ajusta el base o el offset de Airbnb" (FR-008-espíritu aplicado a offsets).
3. **Precio efectivo (US2)**: cálculo derivado `base × (1 + pct/100)` con redondeo a entero COP (documentado). La conversión de moneda del canal es neutra en valor (mismo importe expresado en USD) y se anota en la UI ("Airbnb muestra el equivalente en la moneda del huésped"). Sin cambios en la respuesta del calendario: la web compone base × offsets del endpoint nuevo; el agente usa su tool.
4. **Alcance de promociones (R2)**: `channels_scope: list["booking"|"airbnb"] | None` (None = todos, default actual). El adaptador escribe SOLO los tokens gestionados excluidos como `{token: {"enable": false}}` (clave **`enable`** según payload real; el resto de canales no se toca). El alcance se guarda en `Promotion.conditions["channels_scope"]` y se muestra en preview/lista. Advertencia de doble descuento ampliada a los descuentos nativos de Airbnb (texto, patrón existente).
5. **Auditoría/reversibilidad (FR-003)**: cada apply de offset crea un registro append-only en `channel_offset_log` (before/after pct, origen chat/manual, detail JSON con los multiplier antes/después); revertir = aplicar `before_pct` (misma vía con confirmación). (Ajuste sobre el plan original: AgentAction exige conversation_id — solo chat.)
6. **Validación (FR-004)**: pct ∈ [−50, +100] con 2 decimales; nunca produce precio ≤ 0 dado base > 0.
7. **Deep-links Airbnb (US4)**: `airbnbMulticalendar` (descuentos semanal/mensual y precios del anuncio) y `beds24AirbnbPromotions` (`pagetype=syncroniserairbnbpromotions`); guía de 3 vías en Ofertas (promos de precio con alcance · deals badge Booking · descuentos/promos Airbnb).
8. **ADR 0004**: "Offset por canal como multiplier componible del Channel Manager" (por qué no slots de precio por canal ni gestión del CONVERT desde el dominio).

## Complexity Tracking

Sin violaciones — no aplica.
