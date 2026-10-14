import { NextRequest } from "next/server";

// Página pública (feature 030): reenvía SOLO estas rutas sin sesión a la API privada, con la IP
// del visitante en `x-client-ip` (la API la convierte en un HMAC diario para el límite; no la
// guarda). Ninguna otra cabecera del navegador pasa.
const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const ALLOWED: Record<string, "GET" | "POST"> = {
  municipalities: "GET",
  report: "POST",
  waitlist: "POST",
  visit: "POST",
};

function visitorIp(req: NextRequest): string {
  return (
    req.headers.get("cf-connecting-ip") ??
    req.headers.get("x-real-ip") ??
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    "unknown"
  );
}

async function handle(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const name = (path ?? []).join("/");
  if (ALLOWED[name] !== req.method) {
    return Response.json({ detail: "No encontrado" }, { status: 404 });
  }
  const headers: Record<string, string> = { "x-client-ip": visitorIp(req) };
  let body: string | undefined;
  if (req.method === "POST") {
    headers["content-type"] = "application/json";
    body = await req.text();
    if (body.length > 4000) return Response.json({ detail: "Demasiado grande" }, { status: 413 });
  }
  try {
    const r = await fetch(`${API}/public/${name}${req.nextUrl.search}`, {
      method: req.method,
      headers,
      body,
      cache: "no-store",
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return Response.json({ detail: "API no disponible" }, { status: 502 });
  }
}

export const GET = handle;
export const POST = handle;
export const dynamic = "force-dynamic";
