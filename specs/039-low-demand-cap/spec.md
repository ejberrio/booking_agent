# Feature Specification: Techo p75 con demanda baja

**Branch**: `039-low-demand-cap` · **Created**: 2026-10-20 · **Input**: tras la 038, con el calendario casi vacío el motor volvía a proponer subidas de +15–30 % por eventos medianos (ferias, teatro). Decisión del anfitrión: "haz esa mejora del p75".

## Requirements
- **FR-001 Demanda baja:** menos del 30 % de las noches de los próximos 30 días ocupadas o bloqueadas (`LOW_DEMAND_WINDOW`, `LOW_DEMAND_OCC`).
- **FR-002** Con demanda baja, el techo de mercado de una noche es el **p75**, salvo que esa noche tenga un **evento grande** (relevancia alta: DAVIarena, estadio…) o un **festivo o puente**, que siguen con el **p90**.
- **FR-003** Con demanda normal o alta no cambia nada respecto a la 038 (techo p90).
- **FR-004** El factor `market_cap` indica el nivel (`level`: p75 o p90) y la razón ("ocupación baja: evento pequeño o mediano"), en es/en/pt.
- **FR-005** Sin percentiles de mercado para la zona y el tamaño, no hay techo, igual que antes.

## Tasks
- [x] T001 `MarketCap.level`; etiqueta del factor
- [x] T002 `suggestion_engine`: `low_demand` + `_cap_for`
- [x] T003 Web: texto del factor según el nivel
- [x] T004 Tests: mediano con demanda baja → p75; puente → p90; demanda normal → p90
