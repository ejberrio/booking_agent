import { NextRequest } from "next/server";

// Entrada PÚBLICA de los avisos de reservas de Beds24 (feature 020), sin sesión.
// Solo POST, cuerpo acotado, y reenvío a la API privada de ÚNICAMENTE el cuerpo y la
// cabecera de clave. Sin logs: el cuerpo trae datos del huésped y tokens de pago.
const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const KEY_HEADER = "x-staylever-key";
const MAX_BYTES = 256 * 1024;

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export async function POST(req: NextRequest): Promise<Response> {
  const declared = Number(req.headers.get("content-length") ?? "0");
  if (declared > MAX_BYTES) return json(413, { detail: "Aviso demasiado grande" });
  const body = await req.arrayBuffer();
  if (body.byteLength > MAX_BYTES) return json(413, { detail: "Aviso demasiado grande" });

  const headers = new Headers({ "content-type": "application/json" });
  const key = req.headers.get(KEY_HEADER);
  if (key) headers.set(KEY_HEADER, key);

  let upstream: Response;
  try {
    upstream = await fetch(`${API}/hooks/beds24`, {
      method: "POST",
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    // 502 → Beds24 reintentará más tarde (la API no estaba disponible).
    return json(502, { detail: "API no disponible" });
  }
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { "content-type": "application/json" },
  });
}

export const dynamic = "force-dynamic";
