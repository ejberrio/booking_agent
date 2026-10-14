import { NextRequest, NextResponse } from "next/server";
import { callAuth, redirectTo } from "@/lib/server/auth-api";

// Entrar con Google (feature 026, entrega 4): la API guarda el estado y el verificador PKCE y
// devuelve la URL de Google. `client=app` lo abre la app en el navegador del sistema, con el
// `challenge` del verificador que la app guarda para el traspaso.
export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams;
  const mode = q.get("mode") === "register" ? "register" : "login";
  const client = q.get("client") === "app" ? "app" : "web";
  const { status, data } = await callAuth(req, "google/start", {
    mode,
    client,
    invite_code: q.get("invite") || null,
    challenge: q.get("challenge") || null,
    language: q.get("lang") || "es",
    accept_terms: q.get("accept") === "1",
    report: q.get("report") || null,
  });
  if (status === 200 && typeof data.url === "string") return NextResponse.redirect(data.url, 303);
  const code = typeof data.code === "string" ? data.code : "google_failed";
  return redirectTo(req, `/${mode === "register" ? "register" : "login"}?error=${code}`);
}
