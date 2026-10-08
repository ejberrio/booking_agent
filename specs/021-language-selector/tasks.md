# Tasks: Selector de idioma (español, inglés, portugués)

**Input**: Design documents from `/specs/021-language-selector/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/preferences-api.md, quickstart.md

**Tests**: pytest para preferencia/chat/factores; para la web, la verificación es de tipos (catálogos completos) + build + revisión visual en los 3 idiomas.

**Organization**: Foundational (infra i18n + preferencia) → US1 (traducir toda la UI, por áreas) → US2 (formatos) → US3 (mensajes del servidor + factores) → US4 (chat) → US5 (verificación) → Polish.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational (bloqueante)

- [X] T001 Catálogos por área en `apps/web/lib/i18n/catalog/<área>.ts` (cada archivo exporta `es` y `en`/`pt` tipados `typeof es`, los tres idiomas lado a lado para revisarlos fácil) y `apps/web/lib/i18n/es.ts` (export `es`, `type Messages = typeof es`, `type Lang = "es"|"en"|"pt"`) con la estructura por secciones (`nav, common, login, dashboard, calendar, chat, suggestions, offers, connection, settings, format`) y stubs `apps/web/lib/i18n/en.ts` / `pt.ts` tipados `Messages`
- [X] T002 Crear `apps/web/lib/i18n/index.tsx`: `I18nProvider` (estado `lang`; inicial = cookie `lang` → idioma del navegador si `es|en|pt` (cualquier variante) → `es`), `useI18n()` → `{lang, setLang, t, fmt}`; `t(path, params?)` con interpolación `{x}`; `setLang` escribe cookie (`Max-Age=31536000; SameSite=Lax; Path=/`), actualiza `document.documentElement.lang` y, si hay sesión, `PUT /preferences`; tras montar con sesión, `GET /preferences` y adopta la del servidor si difiere
- [X] T003 Refactor `apps/web/lib/format.ts`: funciones con parámetro `locale` (`formatCOP`, `monthLabel`, `shortDate`, `shortRange`, `pctChange`, días de la semana) usando `Intl` con `es-CO`/`en-US`/`pt-BR` y moneda COP; `fmt` en `useI18n` las expone ligadas al idioma activo
- [X] T004 Montar el provider en `apps/web/components/providers.tsx` y leer la cookie en `apps/web/app/layout.tsx` para `<html lang>` inicial
- [X] T005 [P] API: modelo `apps/api/app/models/preference.py` (`AppPreference`, fila única, `language` String(5) default "es"), migración `apps/api/migrations/versions/b5c6d7e8f9a0_app_preference.py` (down `a4b5c6d7e8f9`), ruta `apps/api/app/api/routes/preferences.py` (`GET/PUT /preferences`, 422 si no es es/en/pt) registrada en `apps/api/app/api/router.py`; `apps/web/lib/api.ts` `getPreferences/putPreferences`
- [X] T006 [P] Test `apps/api/tests/test_preferences.py`: default es; PUT en → GET en; PUT xx → 422; fila única tras varios PUT
- [X] T007 Selector `apps/web/components/i18n/language-switcher.tsx` (Español · English · Português, cada uno en su idioma) en el menú lateral (`components/layout/sidebar.tsx`, también en móvil) y en `app/login/page.tsx`

**Checkpoint**: el selector cambia el idioma (aunque aún pocos textos estén traducidos) y se recuerda.

---

## Phase 2: User Story 1 — Toda la interfaz traducida (P1) 🎯 MVP

Cada tarea: reemplazar literales por `t(...)`, agregar las claves en `es.ts` y sus traducciones en `en.ts` y `pt.ts`.

- [X] T008 [US1] Layout y navegación: `components/layout/sidebar.tsx`, `components/layout/theme-toggle.tsx`, `app/login/page.tsx`, `app/layout.tsx` (metadata description)
- [X] T009 [US1] Dashboard: `app/(app)/page.tsx`, `components/dashboard/kpi.tsx`
- [X] T010 [US1] Calendario: `app/(app)/calendar/page.tsx`, `components/calendar/price-calendar.tsx` (leyenda, días), `range-editor.tsx` (vistas previas de precio y disponibilidad), `day-info-panel.tsx`, `offers-panel.tsx`, `suggestion-panel.tsx`
- [X] T011 [US1] Chat: `app/(app)/chat/page.tsx`, `components/chat/chat-panel.tsx` (incluye tarjetas de confirmación: identificar qué textos vienen del servidor y traducirlos con `server-messages.ts` o componerlos en la web desde datos estructurados)
- [X] T012 [US1] Sugerencias: `app/(app)/suggestions/page.tsx`, `components/suggestions/suggestion-block.tsx`, `batch-preview-dialog.tsx`
- [X] T013 [US1] Ofertas: `app/(app)/offers/page.tsx`
- [X] T014 [US1] Conexión/onboarding: `app/(app)/onboarding/page.tsx`
- [X] T015 [US1] Configuración: `app/(app)/settings/page.tsx` (todas las tarjetas: integración, avisos en tiempo real + guía, precio por canal, POIs, escaneo, secretos + guías `SECRET_HELP`, auditoría)

---

## Phase 3: User Story 2 — Formatos (P1)

- [X] T016 [US2] Sustituir en todos los componentes los usos directos de `formatCOP/monthLabel/shortDate/shortRange/pctChange/toLocaleString("es-CO")` por `fmt.*` del idioma activo; encabezados de días del calendario desde `Intl`

---

## Phase 4: User Story 3 — Mensajes del servidor (P2)

- [X] T017 [US3] `apps/web/lib/i18n/server-messages.ts`: traducciones en/pt de los mensajes de la API (detail de rutas y errores de servicios mostrados al host: vista previa obsoleta, sugerencia resuelta/vencida, regla de precios, promociones, secretos, avisos, canal) con coincidencias exactas y patrones con parámetros; `translateServer(msg, lang)` con respaldo al español; aplicar en UN solo punto: `req()` de `lib/api.ts` traduce el `detail` con el idioma activo (registrado por el provider) antes de lanzar el `Error`, así todos los avisos de error quedan cubiertos sin tocarlos uno a uno y en motivos de omisión/estados (`reservada`, `bloqueada`, `pasada`, `fuera de límites`, `sugerencia resuelta`, `conflicto`, motivos de fallo del lote)
- [X] T018 [US3] API `apps/api/app/domain/suggestion.py`: factores con campos estructurados aditivos (`event.relevance`; `gap.days`; `market.adr/samples/source/state` y `weight` si `used`); tests nuevos en `apps/api/tests/test_suggestion_v2_domain.py`
- [X] T019 [US3] `apps/web/components/suggestions/rationale.tsx`: componer cada factor por idioma desde los campos estructurados (nombre/lugar/fuente del evento intactos); sin estructura → `label`

---

## Phase 5: User Story 4 — Asistente en mi idioma (P2)

- [X] T020 [US4] API: `ChatRequest.language` (default "es", validado es/en/pt) en `apps/api/app/api/routes/chat.py` (y el endpoint de streaming); `apps/api/app/agent/prompts.py` `system_prompt(..., language)` añade la instrucción final de idioma; pasar el idioma por el flujo del agente
- [X] T021 [US4] Test `apps/api/tests/test_agent_language.py`: el prompt contiene la instrucción para en/pt y no para es por defecto; idioma inválido → 422. SC-004 se valida manualmente (5 preguntas en en y 5 en pt, quickstart paso 6)
- [X] T022 [US4] Web: `lib/api.ts` y `lib/sse.ts` envían `language` con cada mensaje del chat

---

## Phase 6: User Story 5 — Verificación de traducciones (P3)

- [X] T023 [US5] Confirmar que `en.ts`/`pt.ts` tipados `Messages` hacen fallar `npx tsc --noEmit` si falta una clave (prueba: quitar una clave temporalmente) y documentar en `docs/operations.md` cómo corregir o agregar textos

---

## Phase 7: Polish

- [X] T024 Revisión visual en es/en/pt (escritorio y móvil) con la demo local: login, 7 secciones, diálogos, avisos; sin desbordes
- [X] T025 Validación: `uv run ruff check . && uv run pytest -q`; `npx tsc --noEmit && npx eslint app components lib middleware.ts && npm run build`
- [X] T026 `docs/operations.md`: sección "Idiomas (Feature 021)"

## Dependencies & Execution Order

- Phase 1 bloquea todo (T005–T006 en paralelo con T001–T004).
- US1 (T008–T015) en cualquier orden entre sí (archivos distintos; todos tocan `es/en/pt.ts` → secuenciales en la práctica).
- US2 tras US1 por archivo (o junto con cada área).
- US3: T018 independiente (API); T017/T019 tras T001–T003.
- US4: T020–T021 independientes (API); T022 tras T002.
- Polish al final.

## Implementation Strategy

1. Infra + selector + preferencia → MVP visible.
2. Traducir por áreas (más usadas primero: calendario, sugerencias, configuración).
3. Formatos, mensajes del servidor, factores, chat.
4. Un PR (`021-language-selector`); revisión visual en 3 idiomas antes de fusionar.
