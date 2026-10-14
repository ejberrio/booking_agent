import { NextRequest } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

// Proxy server-side hacia la API privada (red interna de Railway).
// El navegador llama a "/api/proxy/<path>"; aquí se reenvía a la API con la sesión del
// usuario (cookie httpOnly → `Authorization: Bearer`). Feature 026.
// API_INTERNAL_URL se lee SOLO en servidor (nunca NEXT_PUBLIC_*).
const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

// Cabeceras que el navegador NO puede imponer: hop-by-hop e identidad.
const DROP = new Set([
  "host",
  "connection",
  "content-length",
  "transfer-encoding",
  "cookie",
  "authorization",
  "x-forwarded-for",
  "x-real-ip",
  "x-client-ip",
]);
// Rutas de acceso SIN sesión: solo las llaman las rutas /api/auth/* de la web.
// Feature 030: /public/* solo por /api/public (que fija la IP del visitante).
const BLOCKED = /^(public\/.*|auth\/(login|register|registration-status|claim|claim-status|verify-email|resend-verification|forgot-password|reset-password|logout|providers|handoff|google\/start|google\/callback))$/;

function json(status: number, body: unknown, clearCookie = false): Response {
  const headers = new Headers({ "content-type": "application/json" });
  if (clearCookie) headers.append("set-cookie", `${SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax`);
  return new Response(JSON.stringify(body), { status, headers });
}

async function handle(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await ctx.params;
  const joined = (path ?? []).join("/");
  if (BLOCKED.test(joined)) return json(404, { detail: "No encontrado" });
  const target = `${API}/${joined}${req.nextUrl.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (!DROP.has(k) && !k.startsWith("x-staylever")) headers.set(key, value);
  });
  const token = req.cookies.get(SESSION_COOKIE)?.value;
  if (token) headers.set("authorization", `Bearer ${token}`);

  const init: RequestInit & { duplex?: "half" } = {
    method: req.method,
    headers,
    redirect: "manual",
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch {
    return json(502, { error: "API no disponible" });
  }
  // Sesión vencida o revocada: se borra la cookie y la web lleva a /login.
  if (upstream.status === 401) {
    return json(401, { detail: "Sesión no válida" }, true);
  }

  // Reenvía status y cuerpo tal cual; soporta streaming (SSE) sin bufferizar.
  const respHeaders = new Headers(upstream.headers);
  respHeaders.delete("content-encoding");
  respHeaders.delete("content-length");
  return new Response(upstream.body, { status: upstream.status, headers: respHeaders });
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;

export const dynamic = "force-dynamic";
