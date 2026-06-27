import { NextRequest } from "next/server";

// Proxy server-side hacia la API privada (red interna de Railway).
// El navegador llama a "/api/proxy/<path>"; aquí se reenvía a la API.
// API_INTERNAL_URL se lee SOLO en servidor (nunca NEXT_PUBLIC_*).
const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

// Headers hop-by-hop que no deben reenviarse.
const HOP = new Set(["host", "connection", "content-length", "transfer-encoding", "cookie"]);

async function handle(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await ctx.params;
  const target = `${API}/${(path ?? []).join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP.has(key.toLowerCase())) headers.set(key, value);
  });

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
    return new Response(JSON.stringify({ error: "API no disponible" }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
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
