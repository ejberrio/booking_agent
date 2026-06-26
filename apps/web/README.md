# Web — Booking AI Agent (Next.js)

Frontend: calendario de precios interactivo, chat agéntico, sugerencias, dashboard, onboarding y configuración. Consume la API FastAPI (no duplica lógica de negocio).

## Requisitos
- Node ≥ 20
- Backend corriendo (ver `apps/api`)

## Arranque
```bash
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL + APP_PASSWORD
npm run dev                  # http://localhost:3000
```
Entra con `APP_PASSWORD`. La contraseña se valida en el servidor de Next.js (cookie httpOnly); no se toca el backend.

## Pantallas
- `/` Dashboard (ocupación, heatmap, eventos, sugerencias)
- `/calendar` Calendario de precios (selección de rango → preview → confirmar)
- `/chat` Chat del agente (streaming SSE, propuestas con Confirmar/Cancelar)
- `/suggestions` Bandeja de sugerencias
- `/onboarding` Conectar Beds24, importar, elegir unidad activa
- `/settings` Estado de integraciones y LLM

## Stack
- Next.js (App Router) + TypeScript + Tailwind v4 + shadcn-style UI
- `@tanstack/react-query` (datos), `sonner` (toasts), `next-themes` (tema), `date-fns`

## Verificación
```bash
npm run build   # typecheck + lint
```

## Notas
- El id de la unidad activa se guarda en `localStorage` (el backend aún no expone listado de unidades).
- La edición de la config de LLM desde la UI requiere un endpoint de configuración en el backend (pendiente).
