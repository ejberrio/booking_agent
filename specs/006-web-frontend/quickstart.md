# Quickstart — Frontend web

Cómo correr y verificar la web una vez implementada (`/speckit-implement`).

## 1. Dependencias

```bash
cd apps/web
npm install   # añade @tanstack/react-query, sonner, date-fns, next-themes
```

## 2. Configuración (`apps/web/.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000   # backend FastAPI
APP_PASSWORD=tu-contraseña-de-acceso         # solo servidor (no NEXT_PUBLIC)
```

## 3. Correr

```bash
# Backend (otra terminal): make db-up && make api   (en la raíz del repo)
cd apps/web && npm run dev   # http://localhost:3000
```
1. **Login**: entra con `APP_PASSWORD`.
2. **Onboarding**: conecta Beds24 (prueba de conexión), importa, elige la propiedad activa.
3. **Calendario**: selecciona un rango, escribe un precio, revisa el diff y confirma.
4. **Chat**: pide un cambio; verás la respuesta en streaming y un botón Confirmar.
5. **Sugerencias**: revisa, aprueba/aplica.
6. **Dashboard**: ocupación, heatmap, eventos y sugerencias.
7. **Configuración**: ajusta el LLM y revisa el estado de las integraciones.

## 4. Verificación

```bash
cd apps/web
npm run build   # typecheck + lint (next build) -> debe pasar sin errores
```
Criterio: la build pasa; los flujos clave (calendario→preview→confirmar, chat→propuesta→confirmar, sugerencias) funcionan contra el backend.
