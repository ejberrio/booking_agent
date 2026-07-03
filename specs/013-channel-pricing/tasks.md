# Tasks: Precios y promociones por canal (Booking.com + Airbnb)

**Input**: Design documents from `/specs/013-channel-pricing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos (Principio IV: adaptadores y lógica de pricing no se mergean sin pruebas; SC-004 exige equivalencia con offsets en 0). Dobles del puerto y httpx.MockTransport; sin APIs reales.

**Organization**: por user story. La verificación EN VIVO (offset +2% reversible y promo de prueba con alcance) va en Polish con confirmación del host — nunca se deja aplicada.

**Regla transversal (FR-012 / SC-004)**: con offsets 0/null y sin `channels_scope`, toda salida existente permanece idéntica; ninguna tarea modifica expectativas de tests previos.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable · **[Story]**: US1 (offset por canal), US2 (precio efectivo), US3 (promos con alcance), US4 (deep-links Airbnb)

## Path Conventions

Monorepo: `apps/api` (FastAPI) y `apps/web` (Next.js). Rutas relativas a la raíz del repo.

---

## Phase 1: Setup

- [X] T001 Crear ADR "Offset por canal como multiplier componible del Channel Manager" (decisión R1, alternativas slots/manual, límite: solo canales con multiplier API — hoy airbnb) en docs/adr/0004-channel-price-offset.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el puerto debe hablar de ajustes por canal antes de cualquier historia.

- [X] T002 Extender puerto en apps/api/app/channels/base.py: métodos `supports_price_adjustment(channel) -> bool`, `get_channel_price_adjustment(property_external_id, channel) -> Decimal | None`, `set_channel_price_adjustment(property_external_id, channel, factor: Decimal | None) -> WriteResult` (docstrings con semántica del contrato) y `RemoteFixedPrice.channels: dict[str, bool] | None = None`
- [X] T003 Implementar en apps/api/app/channels/beds24_v2.py: GET/POST `/channels/settings` (canal airbnb); parseo del sufijo `\*(\d+(?:\.\d+)?)$` como factor propio preservando SIEMPRE el prefijo (p. ej. `*[CONVERT:COP-USD]`); escritura con factor a 4 decimales; verificación post-write por re-GET (verified=False si difiere — endpoint Alpha); `supports_price_adjustment` → {"airbnb"}
- [X] T004 Añadir `channels` al body de fixed prices en apps/api/app/channels/beds24_v2.py `_fixed_price_body`: si `RemoteFixedPrice.channels` no es None, emitir `{"channels": {token: {"enable": flag}}}` solo con los tokens presentes (clave `enable` — payload real; ver research R2)
- [X] T005 [P] Tests del adaptador en apps/api/tests/test_beds24_v2_channel_settings.py: casos 1-6 del contrato channel-manager-port.md (parseo con/sin sufijo, composición preservando prefijo, quitar ajuste restaura prefijo exacto, prefijo vacío, verified=False si re-GET difiere, body de fixed price con channels solo-booking y sin channels por default)

**Checkpoint**: el puerto entrega/escribe ajustes y alcance — historias desbloqueadas.

---

## Phase 3: User Story 1 — Ajuste de precio por canal (Priority: P1) 🎯 MVP

**Goal**: configurar "Airbnb +8%" con preview→confirmar→aplicar→auditar, reversible, honesto para canales sin soporte; default 0 = intacto.

**Independent Test**: con doble del puerto: preview(+8) → fingerprint → apply → Channel.price_offset_pct=8, auditado y verified; apply(0) restaura; booking → error honesto; fuera de rango → 422.

### Tests for User Story 1

- [X] T006 [P] [US1] Tests del servicio en apps/api/tests/test_channel_pricing_service.py: get_offsets (default null/0 + supported por canal); preview con ejemplo base→efectivo y warning de canal inactivo; validación rango [−50,100] y canal no soportado (mensaje honesto, sin persistir); apply con fingerprint válido persiste+audita (AgentAction con before/after pct y multiplier), fingerprint inválido → error; fallo del CM → SyncIssue y price_offset_pct SIN cambiar; apply(0) revierte y audita
- [X] T007 [P] [US1] Tests de endpoints en apps/api/tests/test_channel_offsets_api.py: GET /pricing/channel-offsets; POST preview (422 fuera de rango; honesto para booking); POST apply (409 fingerprint inválido) — contrato pricing-api.md

### Implementation for User Story 1

- [X] T008 [US1] Crear apps/api/app/services/channel_pricing_service.py: `get_offsets(session, adapter)`, `preview_offset(session, adapter, channel, pct)` (fingerprint determinista, ejemplo con el precio base más próximo o 100000, warnings), `apply_offset(session, adapter, channel, pct, fingerprint, origin)` (valida → escribe puerto → persiste Channel.price_offset_pct → audita AgentAction → SyncIssue si no ok/verified, sin persistir en fallo), errores tipados (patrón PromotionError de offer_promotion_service)
- [X] T009 [US1] Endpoints en apps/api/app/api/routes/pricing.py: `GET /pricing/channel-offsets`, `POST /pricing/channel-offsets/preview`, `POST /pricing/channel-offsets/apply` (schemas Pydantic; adapter con aclose(), patrón existente)
- [X] T010 [US1] Suite completa verde: `cd apps/api && uv run pytest -q` (129 previas intactas + nuevas)

**Checkpoint**: US1 completa — control del offset end-to-end por API.

---

## Phase 4: User Story 2 — Ver el precio efectivo por canal (Priority: P2)

**Goal**: app y agente muestran qué percibe el huésped por canal; el agente menciona el efecto por canal al proponer precios.

**Independent Test**: con offset +8 sembrado: tool `get_channel_offsets` lo devuelve; prompt incluye la regla de mencionar efecto por canal; web muestra base y efectivo.

### Tests for User Story 2

- [X] T011 [P] [US2] Tests del agente en apps/api/tests/test_agent_channel_offsets.py: tool `get_channel_offsets` (salida con offset_pct y supported); tool `propose_channel_offset` construye propuesta vía preview del servicio y NO aplica sin confirmación; canal no soportado → propuesta imposible con explicación; prompt contiene la regla de "efecto por canal" y conserva reglas previas

### Implementation for User Story 2

- [X] T012 [US2] Tools en apps/api/app/agent/tools.py: `get_channel_offsets` (read, sin parámetros) y `propose_channel_offset` (write; build_proposal→preview, apply_proposal→apply con origin chat) según contracts/agent-tools.md
- [X] T013 [US2] Regla de offsets en apps/api/app/agent/prompts.py (texto del contrato agent-tools.md; conservar todo lo existente)
- [X] T014 [US2] Web Configuración: tarjeta "Precio por canal" en apps/web/app/(app)/settings/page.tsx (lista canales con offset y supported; editar → preview con ejemplo → confirmar → toast; deshabilitado con explicación para no soportados) + métodos/tipos en apps/web/lib/api.ts y apps/web/lib/types.ts (`ChannelOffset`, `OffsetPreview`, getChannelOffsets/previewChannelOffset/applyChannelOffset)
- [X] T015 [US2] Precio efectivo visible en apps/web/app/(app)/settings/page.tsx (ejemplo del preview) y nota "Airbnb lo muestra en la moneda del huésped" (R3)
- [X] T015b [US2] Precio efectivo por canal en el detalle de día del calendario web (apps/web/app/(app)/calendar/page.tsx o el componente del panel de día): cuando exista offset ≠ 0, mostrar "Booking: X · Airbnb: ~Y (+8%)" calculado de base × offsets (api.getChannelOffsets, cacheado); con offsets 0/null el panel queda EXACTAMENTE igual que hoy (FR-012); `npm run build` verde (cubre US2-AS1/FR-005 — remediación C1 del analyze)

**Checkpoint**: US2 completa — visibilidad en chat y web.

---

## Phase 5: User Story 3 — Promociones con alcance de canal (Priority: P2)

**Goal**: preview/lista de promociones muestran alcance; se puede limitar a canales; advertencia de doble descuento cubre ambos canales.

**Independent Test**: crear promo con scope ["booking"] vía servicio con doble → body del CM con airbnb.enable=false, conditions con scope, lista lo muestra; sin scope → body sin channels y lista "todos".

### Tests for User Story 3

- [X] T016 [P] [US3] Tests en apps/api/tests/test_offer_promotion_scope.py: preview incluye channels_scope y advertencia doble descuento con texto de ambos canales; scope [] → error; apply con scope pasa `RemoteFixedPrice.channels={"airbnb": False}` al puerto y guarda conditions["channels_scope"]; sin scope → channels=None y conditions sin la clave; list expone channels_scope (null = todos); retire intacto

### Implementation for User Story 3

- [X] T017 [US3] Alcance en apps/api/app/services/offer_promotion_service.py: parámetro `channels_scope: list[ChannelKind] | None` en preview/apply (validar no vacío y tokens gestionados); construir `RemoteFixedPrice.channels` con los gestionados EXCLUIDOS en False; persistir en conditions; exponer en list y en PromotionPreview/PromotionView (apps/api/app/schemas/promotion.py); ampliar advertencia de doble descuento (deals Booking + descuentos semanal/mensual Airbnb)
- [X] T018 [US3] Endpoints en apps/api/app/api/routes/pricing.py: `channels_scope` opcional en OfferPromoPreviewRequest/ApplyRequest; propagar al servicio; incluir en respuestas
- [X] T019 [US3] Tools del agente: parámetro opcional `channels_scope` en `propose_offer_promotion` (enum booking/airbnb, array) en apps/api/app/agent/tools.py y mención en el prompt (apps/api/app/agent/prompts.py: "si el host pide una promo solo para un canal, usa channels_scope")
- [X] T020 [US3] Web Ofertas: selector de alcance (checkboxes Booking/Airbnb, default ambos) en el formulario, alcance en preview y en la lista ("Todos los canales" / "Solo Booking.com"), en apps/web/app/(app)/offers/page.tsx + tipos/método en apps/web/lib/{types.ts,api.ts}; suite api + build web verdes

**Checkpoint**: US3 completa — alcance visible y controlable.

---

## Phase 6: User Story 4 — Deep-links de Airbnb (Priority: P3)

**Goal**: acceso en un clic a los deals nativos de Airbnb con guía de 3 vías.

**Independent Test**: la sección Ofertas muestra los enlaces de Airbnb y la guía distingue promos de precio / deals badge Booking / descuentos Airbnb.

### Implementation for User Story 4

- [X] T021 [P] [US4] Enlaces en apps/web/lib/links.ts: `airbnbMulticalendar` (https://www.airbnb.com/multicalendar — precios y descuentos semanal/mensual del anuncio) y `beds24AirbnbPromotions` (https://beds24.com/control3.php?pagetype=syncroniserairbnbpromotions), con comentarios
- [X] T022 [US4] Guía de 3 vías y botones de Airbnb en la tarjeta de deals de apps/web/app/(app)/offers/page.tsx (título neutro "¿Y los deals nativos de los canales?"; distinguir: promos de precio con alcance — app; deals badge Booking — Beds24; descuentos/promos Airbnb — Airbnb); `npm run build` verde

**Checkpoint**: US4 completa — paridad de navegación.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T023 [P] Documentar en docs/operations.md: sección "Precio por canal" (qué es el offset, cómo se compone con la conversión de moneda, honestidad Booking=base, alcance de promociones, advertencia doble descuento, y nota C3: en Airbnb una promoción recibe ADEMÁS el ajuste del canal — allowMultiplier default)
- [X] T024 Verificación EN VIVO acotada y reversible (⚠️ con confirmación del host, quickstart.md): (a) capturar el payload COMPLETO de GET /channels/settings ANTES; offset +2% en Airbnb → verificar multiplier `*[CONVERT:COP-USD]*1.02` por GET y precio en multicalendario; verificar que currency, roomTypes y demás campos NO enviados quedaron INTACTOS (endpoint Alpha — remediación C2; si algo cambió, abortar, restaurar y documentar); REVERTIR a 0 y confirmar prefijo exacto; (b) promo de prueba fechas +300 días con scope solo-booking → verificar channels.airbnb.enable=false en GET /inventory/fixedPrices; RETIRAR de inmediato; si el POST rechaza la clave `enable`, probar `enabled` y actualizar contrato+adaptador
- [X] T025 Quickstart/checklist al día si hubo divergencias; `uv run pytest -q` + `npm run build` finales; preparar PR (squash a main con gh auth switch --user ejberrio)

---

## Dependencies & Execution Order

- **Setup (T001)** ∥ con Foundational. **Foundational (T002→T003/T004, T005)** bloquea todo.
- **US1 (T006-T010)**: tras Foundational. 🎯 MVP.
- **US2 (T011-T015)**: usa el servicio de US1 (T008) → tras US1.
- **US3 (T016-T020)**: solo necesita Foundational (T004) → puede ir en paralelo con US1/US2.
- **US4 (T021-T022)**: independiente (solo web) → cualquier momento.
- **Polish (T023-T025)**: al final; T024 requiere deploy o túnel al CM real + confirmación del host.

```text
T001 ∥ [T002 → {T003, T004} → T005]
    → US1: {T006, T007} → T008 → T009 → T010
    → US3: T016 → T017 → T018 → T019 → T020        (∥ con US1 tras T004)
US1 → US2: T011 → T012 → T013 → {T014 → T015}
US4: {T021} → T022                                  (∥ con todo)
→ {T023} → T024 → T025
```

### Parallel opportunities

- T003 ∥ T004 (mismo archivo — mejor secuencial; T005 tras ambos). T001 ∥ Foundational.
- US3 ∥ US1 (servicios distintos); US4 ∥ todo (solo web).
- T006 ∥ T007; T021 ∥ T023.

## Implementation Strategy

1. **MVP**: Foundational + US1 (offset end-to-end por API) — ya desplegable y útil vía curl/app.
2. **Incremento 2**: US2 (agente + web) — el control llega al chat y a Configuración.
3. **Incremento 3**: US3 (alcance de promos) + US4 (links).
4. Polish: docs + verificación en vivo reversible (con el host) + PR único squash a main.
