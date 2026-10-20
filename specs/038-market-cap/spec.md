# Feature Specification: Techo de mercado (p90) para las sugerencias

**Branch**: `038-market-cap` · **Created**: 2026-10-20 · **Input**: piloto de mercado (#148). PriceLabs y Apify coincidieron: en puentes y eventos el anfitrión cobraba por encima del p90 de su zona y tenía 102 de 104 noches vacías. Decisión del anfitrión: "implementa el techo por evento con el p90" y balancear las fechas de evento con el mercado.

## Requirements
- **FR-001 Percentiles de mercado por zona, habitaciones y fecha** (`market_band`: p25, p50, p75 y p90 por noche, sin cargos):
  - la zona es la ciudad principal del área metropolitana;
  - 0 habitaciones = todas;
  - son datos de plataforma, agregados, sin anuncios ni personas.
- **FR-002 Importación por el administrador de plataforma:** `POST /admin/market-bands` (`city`, `bedrooms`, `source`, `rows` [[fecha, p25, p50, p75, p90]]) y `GET /admin/market-bands` (resumen). Fuente inicial: PriceLabs Market Dashboard → "Precios Futuros".
- **FR-003 Habitaciones de la unidad:** `unit_type.bedrooms`; si falta, se deducen del nombre ("Three-Bedroom", "3BR", "3 habitaciones").
- **FR-004 Motor de sugerencias:**
  - si la sugerencia, con evento u ocupación, pasa del **p90** de esa noche, se recorta al p90;
  - si el precio del anfitrión ya está **por encima del p90**, se sugiere bajar hacia el p90, con el tope bajista de −15 % (gradual), aunque no haya evento;
  - nuevo factor `market_cap` ("techo de mercado: el 90 % de la zona cobra hasta ~X") en es/en/pt;
  - sin datos de mercado, todo funciona igual que antes.
- **FR-005** No se publica nada solo: las sugerencias se siguen aprobando (principio III).

## Fuera de alcance (siguiente)
- Carga del CSV desde la web de Administración.
- Actualización automática (requiere licencia o API).
- Usar el p50/p75 para el precio objetivo en fechas normales.

## Tasks
- [x] T001 `MarketBand` + `unit_type.bedrooms` + migración `c9d0e1f2a3b5`
- [x] T002 `MarketCap` en `suggest_price_v2`; `market_band_service` (`import_rows`, `caps_for`, `unit_bedrooms`, `summary`)
- [x] T003 Motor (`suggestion_engine`) + rutas de administración
- [x] T004 Web: factor `market_cap` (es/en/pt)
- [x] T005 Tests `tests/test_market_cap.py`
