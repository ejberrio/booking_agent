# Web — Booking AI Agent (Next.js)

Frontend: chat agéntico, calendario de precios y dashboard.

## Requisitos
- Node ≥ 20

## Arranque
```bash
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL apunta a la API
npm run dev                  # http://localhost:3000
```

La API debe estar corriendo en `:8000` (ver `apps/api`).

## Stack
- Next.js (App Router) + TypeScript
- Tailwind CSS v4 + shadcn/ui (añade componentes con `npx shadcn@latest add <name>`)
- lucide-react (iconos)

## Estructura
```
app/        # rutas (App Router)
components/  # UI (chat, api-status, ui/*)
lib/         # api.ts (fetch a la API), utils.ts (cn)
```
