import { NextRequest, NextResponse } from "next/server";
import { callAuth, redirectTo, redirectWithSession } from "@/lib/server/auth-api";

const APP_RETURN = "com.staylever.app://auth";

/** La app de Android: Google se abrió en el navegador del sistema; se vuelve a la app con un
 *  código de traspaso de un solo uso (la app lo canjea con su verificador). Página con botón
 *  por si el navegador no abre la app solo. */
function backToApp(params: string) {
  const href = `${APP_RETURN}?${params}`;
  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>StayLever</title>
<style>body{font-family:system-ui,sans-serif;background:#0a0a0a;color:#fafafa;display:grid;
place-items:center;min-height:100vh;margin:0;text-align:center;padding:16px}
a{display:inline-block;margin-top:16px;padding:12px 20px;border-radius:8px;background:#2563eb;
color:#fff;text-decoration:none}</style></head><body><div><p>Volviendo a StayLever…</p>
<a href="${href}">Abrir la app</a></div>
<script>location.replace(${JSON.stringify(href)});</script></body></html>`;
  return new NextResponse(html, {
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
  });
}

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams;
  const code = q.get("code");
  const state = q.get("state");
  if (!code || !state) {
    // El usuario canceló en Google (o llegó sin parámetros).
    return redirectTo(req, "/login?error=google_cancelled");
  }
  const { status, data } = await callAuth(req, "google/callback", { code, state });
  if (status === 200 && data.client === "app" && typeof data.handoff_code === "string") {
    return backToApp(`code=${encodeURIComponent(data.handoff_code)}`);
  }
  if (status === 200 && typeof data.token === "string") {
    return redirectWithSession(req, data.token, "/");
  }
  const err = typeof data.code === "string" ? data.code : "google_failed";
  const page = err === "invite_required" || err === "invite_invalid" ? "register" : "login";
  return redirectTo(req, `/${page}?error=${err}`);
}
