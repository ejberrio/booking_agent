# Contrato: Proxy web → API (red privada)

El navegador nunca habla con la API directamente. La web expone un proxy server-side.

## Ruta

- Handler: `app/api/proxy/[...path]/route.ts` (Next App Router), métodos GET/POST/PUT/PATCH/DELETE.
- El navegador llama a `"/api/proxy/<path>"` (mismo origen).
- El handler reenvía a `${API_INTERNAL_URL}/<path>` preservando: método, query string, headers relevantes (Content-Type, Accept) y body.
- Devuelve el status y el cuerpo del upstream **sin transformar**. Para respuestas en streaming (SSE de `/chat/stream`), reenvía el `ReadableStream` sin bufferizar.

## Seguridad

- `API_INTERNAL_URL` se lee **solo en servidor** (jamás `NEXT_PUBLIC_`); no llega al bundle del navegador.
- El proxy queda bajo el `middleware` de auth: toda ruta salvo `/login` y `/api/login` exige la cookie `session`. Por tanto `/api/proxy/*` solo funciona autenticado.
- No se reenvían cookies de sesión a la API (la API no las usa); el handler puede filtrar headers de hop-by-hop.

## Mapeo de `lib/api.ts`

- `API_URL` pasa de `process.env.NEXT_PUBLIC_API_URL` a la base relativa `"/api/proxy"`.
- El resto de funciones (`getCalendar`, `applyRange`, chat SSE, etc.) no cambian su forma, solo el prefijo.

## Casos límite

- Upstream 4xx/5xx → se propaga el mismo status y cuerpo.
- API privada inaccesible → el proxy responde `502 Bad Gateway` con mensaje genérico (sin filtrar el host interno).
- Timeouts → mensaje genérico; no exponer detalles de red.
