# Implementation Plan: Selector de idioma (español, inglés, portugués)

**Branch**: `021-language-selector` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/021-language-selector/spec.md` · issue #124

## Summary

i18n ligera y tipada, sin dependencias nuevas:

1. **Catálogos en la web** (`apps/web/lib/i18n/catalog/<área>.ts`, cada uno con `es`, `en`, `pt` lado a lado; `lib/i18n/messages.ts` los compone): el español es la referencia; `en`/`pt` se tipan con la forma de `es`, así **TypeScript falla el build si falta un texto** (FR-007/SC-005). Interpolación simple `{name}` y plurales mínimos con dos claves.
2. **`I18nProvider` + `useI18n()`** → `{ lang, setLang, t, fmt }`. `fmt` envuelve `Intl` con `es-CO` / `en-US` / `pt-BR` y moneda **COP** (FR-008/009). El cambio re-renderiza sin recargar (FR-002).
3. **Preferencia**: cookie `lang` (1 año, también en el login, sin sesión) + **preferencia del host en la API** (`GET/PUT /preferences`, tabla `app_preference` de una fila) para que valga en todos los dispositivos (FR-003). Primera visita: idioma del navegador si es es/en/pt (cualquier variante), si no español (FR-004).
4. **Mensajes del servidor** (FR-010/011): el servidor sigue hablando español (referencia); la web los traduce con un **catálogo de mensajes del servidor** (coincidencia exacta + patrones con parámetros) y, si no hay traducción, muestra el español. Motivos de omisión y estados ya son vocabulario cerrado.
5. **Explicación de sugerencias**: el motor añade **campos estructurados** a cada factor (relevancia, %, días, ADR, muestras, peso, estado del mercado) además del `label` en español; la web arma la frase en el idioma elegido y conserva el nombre del evento. Datos viejos sin estructura → se muestra el `label` (español) (supuesto de la spec).
6. **Asistente**: el chat envía `language`; el system prompt añade "Responde siempre en {idioma}" (FR-012). Las confirmaciones son componentes de la web → se traducen como el resto (FR-013).

El comportamiento funcional no cambia (FR-014): solo textos, formatos y una preferencia.

## Technical Context

**Language/Version**: TypeScript / Next.js 15 (web, grueso del trabajo), Python 3.12 (API: preferencia, chat, factores estructurados)
**Primary Dependencies**: existentes (`Intl` nativo, React context); SIN librerías de i18n nuevas
**Storage**: PostgreSQL / SQLite tests. **Una migración** (`b5c6d7e8f9a0`, down `a4b5c6d7e8f9`): tabla `app_preference` (fila única: `language`)
**Testing**: `tsc` (catálogos completos por tipo) + pytest (preferencia, prompt con idioma, factores estructurados); revisión visual en es/en/pt con la demo local
**Target Platform**: Railway (web + api)
**Project Type**: monorepo web application
**Performance Goals**: cambio de idioma < 1 s, sin recarga (catálogos empaquetados, ~3 × 15 KB)
**Constraints**: español como referencia; contenido del host/terceros sin traducir; no romper 291 tests; sin cambios de comportamiento
**Scale/Scope**: ~31 componentes web (~400 textos), 3 endpoints API, 1 migración

## Constitution Check

| Principio | Evaluación |
|---|---|
| I. Spec-Driven | ✅ ciclo completo |
| II. Provider-agnostic | ✅ la instrucción de idioma va en el prompt común (LiteLLM, cualquier proveedor) |
| III. Human-in-the-loop | ✅ sin cambios en flujos de escritura; las vistas previas/confirmaciones solo cambian de texto |
| IV. Tipado y pruebas | ✅ catálogos tipados (texto faltante = error de compilación); tests de preferencia y prompt |
| V. Simplicidad | ✅ sin librería de i18n ni rutas por idioma (`/en/...`): contexto + diccionarios; el servidor no se traduce, solo la web |

**Post-diseño (re-check)**: ✅ sin violaciones.

## Project Structure

### Documentation (this feature)

```text
specs/021-language-selector/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/preferences-api.md
└── checklists/requirements.md
```

### Source Code

```text
apps/web/
├── lib/i18n/catalog/<área>.ts                # catálogos por área: es (referencia) + en/pt tipados
├── lib/i18n/messages.ts                      # compone las áreas → Messages por idioma
├── lib/i18n/server-messages.ts               # traducciones de mensajes del servidor (exactos + patrones)
├── lib/i18n/index.tsx                        # I18nProvider, useI18n (t, fmt, lang, setLang), detección
├── lib/format.ts                             # funciones con parámetro de idioma (fmt las envuelve)
├── components/i18n/language-switcher.tsx     # selector (menú lateral y login)
├── components/suggestions/rationale.tsx      # arma la explicación desde factores estructurados
├── app/layout.tsx · components/providers.tsx # monta el provider (lee cookie `lang`)
└── TODOS los componentes/páginas con texto   # t("…") en lugar de literales

apps/api/
├── app/models/preference.py + migración b5c6d7e8f9a0
├── app/api/routes/preferences.py             # GET/PUT /preferences {language}
├── app/api/routes/chat.py · app/agent/*      # language → instrucción en el system prompt
├── app/domain/suggestion.py                  # factores con campos estructurados
└── tests/test_preferences.py · test_agent_language.py · (+ casos en test_suggestion_v2_domain.py)
```

## Decisiones clave (detalle en research.md)

1. Diccionarios tipados propios en vez de `next-intl`/`i18next` (una sola pantalla de app, sin rutas por idioma, ~400 textos).
2. Cookie + preferencia en servidor: el login (sin sesión) usa cookie/navegador; tras entrar, la preferencia del servidor manda y actualiza la cookie.
3. Traducción de mensajes del servidor en la web (no en la API): un único lugar de traducciones, el español queda como referencia y respaldo.
4. Factores estructurados en el motor (aditivo, retrocompatible).
5. Variantes: `es-CO`, `en-US`, `pt-BR` para formatos.

## Complexity Tracking

Sin violaciones que justificar.
