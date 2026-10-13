import { NextRequest, NextResponse } from "next/server";
import {
  LEGACY_COOKIE,
  SESSION_COOKIE,
  sessionKindFor,
  sessionMaxAgeFor,
} from "@/lib/session";

// Rutas de acceso de la web (feature 026): llaman a la API privada desde el servidor y
// ponen/quitan la cookie httpOnly. El navegador nunca ve la API ni un token en JS.
const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export function clientIp(req: Request): string | null {
  return req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || null;
}

export async function callAuth(
  req: Request,
  path: string,
  body?: unknown,
  method: "POST" | "GET" = "POST",
): Promise<{ status: number; data: Record<string, unknown> }> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  const ua = req.headers.get("user-agent");
  if (ua) headers["user-agent"] = ua;
  try {
    const r = await fetch(`${API}/auth/${path}`, {
      method,
      headers,
      body: method === "POST" ? JSON.stringify(body ?? {}) : undefined,
      cache: "no-store",
    });
    const text = await r.text();
    return { status: r.status, data: text ? JSON.parse(text) : {} };
  } catch {
    return { status: 502, data: { detail: "API no disponible" } };
  }
}

export function kindFor(req: Request) {
  return sessionKindFor(req.headers.get("user-agent"));
}

/** Respuesta con la cookie de sesión puesta (y la cookie antigua borrada). */
export function withSession(req: Request, token: string, body: unknown = { ok: true }) {
  const res = NextResponse.json(body);
  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: sessionMaxAgeFor(req.headers.get("user-agent")),
    secure: process.env.NODE_ENV === "production",
  });
  res.cookies.set(LEGACY_COOKIE, "", { path: "/", maxAge: 0 });
  return res;
}

export function relay(status: number, data: Record<string, unknown>) {
  return NextResponse.json(data, { status });
}

/** Origen público de la petición. Detrás del proxy de Railway `req.nextUrl` trae la dirección
 *  interna del contenedor (p. ej. https://[::]:8080), así que se usa el host que vio el navegador. */
export function publicOrigin(req: NextRequest): string {
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? req.nextUrl.host;
  const proto =
    req.headers.get("x-forwarded-proto")?.split(",")[0]?.trim() ??
    req.nextUrl.protocol.replace(":", "");
  return `${proto}://${host.split(",")[0].trim()}`;
}

/** Redirección dentro de la web (mismo dominio que la petición). */
export function redirectTo(req: NextRequest, path: string) {
  return NextResponse.redirect(new URL(path, publicOrigin(req)), 303);
}

/** Redirección con la cookie de sesión puesta (Entrar con Google y traspaso a la app). */
export function redirectWithSession(req: NextRequest, token: string, path = "/") {
  const res = redirectTo(req, path);
  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: sessionMaxAgeFor(req.headers.get("user-agent")),
    secure: process.env.NODE_ENV === "production",
  });
  res.cookies.set(LEGACY_COOKIE, "", { path: "/", maxAge: 0 });
  return res;
}
