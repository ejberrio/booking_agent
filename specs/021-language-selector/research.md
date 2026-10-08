# Research: Selector de idioma (021)

## R1. ¿Librería de i18n o diccionarios propios?

- **Decision**: diccionarios propios en TypeScript (`es.ts` como fuente de verdad; `en.ts`/`pt.ts` tipados con `Messages = typeof es`) + `React.Context`.
- **Rationale**: ~400 textos, una app autenticada sin SEO ni rutas por idioma; el tipado da la verificación de textos faltantes gratis en `tsc`/`npm run build` (FR-007, SC-005) y el host puede corregir un texto editando un archivo legible. Principio V.
- **Alternatives**: `next-intl` (rutas `/[locale]`, middleware, más superficie para una app de un usuario); `i18next` (dependencia y claves sin tipado fuerte por defecto).

## R2. ¿Dónde guardar la preferencia?

- **Decision**: cookie `lang` (1 año, `SameSite=Lax`) + `app_preference.language` en la API.
- **Rationale**: la cookie permite idioma correcto en el login (sin sesión) y en el primer render; la preferencia en servidor cumple "todos los dispositivos" (FR-003). Al iniciar sesión, la web lee `GET /preferences` y, si difiere, adopta la del servidor y actualiza la cookie. Cambiar en el selector → cookie + `PUT /preferences` (si hay sesión).
- **Alternatives**: solo localStorage (no viaja entre dispositivos); solo servidor (el login no la conoce).

## R3. Mensajes del servidor

- **Decision**: la API sigue en español; la web traduce con `server-messages.ts`: mapa de textos exactos y patrones (`/^La sugerencia venció \(rango (.+) → (.+), todo en el pasado\)$/` → plantilla con parámetros). Sin coincidencia → español.
- **Rationale**: ~55 mensajes, muchos con parámetros; traducir en la web mantiene un único lugar de traducciones y no toca la lógica de la API ni sus 291 tests. Los motivos de omisión (`reservada`, `bloqueada`, `pasada`, `fuera de límites`, `sugerencia resuelta`, `conflicto`) y los estados de avisos ya son vocabulario cerrado.
- **Alternatives**: códigos de error en la API (`code` + params) → refactor amplio de rutas y servicios; traducción en la API vía `Accept-Language` → catálogos duplicados en dos lenguajes.

## R4. Explicación de sugerencias

- **Decision**: el motor añade a cada factor campos estructurados (aditivos): `event`: `relevance`; `occupancy`: —; `gap`: `days`; `market`: `adr`, `samples`, `weight`, `state ∈ {used, low_confidence, discarded}`. La web compone la frase por idioma; el nombre del evento, lugar y fuente se muestran tal cual.
- **Rationale**: hoy el `label` es español libre ("libre a 5 días (−9%)"); traducirlo con patrones es frágil. Con estructura, la web arma cualquier idioma. Las sugerencias existentes se refrescan solas en el siguiente escaneo (US4 de 019 actualiza el racional de las pendientes); las antiguas sin estructura muestran el `label`.

## R5. Idioma del asistente

- **Decision**: `ChatRequest.language` (opcional, default `es`) → `system_prompt(..., language)` agrega al final: "Responde SIEMPRE en {English|Português (Brasil)|español}, sin importar el idioma del mensaje del host. No traduzcas nombres propios (eventos, huéspedes, promociones)." Las herramientas y montos no cambian.
- **Rationale**: los LLM siguen bien una instrucción explícita al final del system prompt; el idioma viaja por mensaje (cambiar de idioma aplica al siguiente).

## R6. Formatos

- **Decision**: `Intl.NumberFormat(locale, {style: "currency", currency: "COP", maximumFractionDigits: 0})` y `Intl.DateTimeFormat(locale, …)` con `es-CO`/`en-US`/`pt-BR`; `shortDate/shortRange` y nombres de meses/días derivados de `Intl` (no de arrays en español).
