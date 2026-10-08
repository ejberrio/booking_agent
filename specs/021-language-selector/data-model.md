# Data Model: Selector de idioma (021)

## AppPreference (NUEVA, `app_preference`, fila única)

| Campo | Tipo | Nota |
|---|---|---|
| id | int PK | siempre 1 |
| language | String(5) | `es` · `en` · `pt`; default `es` |
| created_at / updated_at | datetime tz | TimestampMixin |

Migración `b5c6d7e8f9a0` (down `a4b5c6d7e8f9`). Se crea al primer `GET`/`PUT` si no existe.

## Factores de sugerencia (existente, JSON en `price_suggestion.rationale.factors[]`)

Campos **aditivos** (el `label` en español se conserva para compatibilidad):

| kind | campos nuevos |
|---|---|
| event | `relevance` (high/medium/low) — `pct` y `event{name, location, dates, source_url}` ya existen |
| occupancy | — (`pct` ya existe) |
| gap | `days` (int) |
| market | `adr` (str), `samples` (int), `source` (str), `weight` (float, solo si `state=used`), `state` (`used`·`low_confidence`·`discarded`) |

## Catálogos (web, no persistidos)

- `Messages` = forma de `es.ts` (objeto anidado por sección: `nav`, `common`, `calendar`, `suggestions`, `offers`, `settings`, `chat`, `dashboard`, `connection`, `login`, `format`).
- `ServerMessages`: `{ exact: Record<string, Record<Lang, string>>, patterns: Array<{ re: RegExp, t: Record<Lang, (m) => string> }> }`.
