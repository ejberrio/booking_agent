import { createHash, timingSafeEqual } from "node:crypto";
import { callAuth, kindFor, relay, withSession } from "@/lib/server/auth-api";

// Reclamar la cuenta nº 1 (feature 026): solo quien conoce la contraseña compartida actual
// (APP_PASSWORD) y solo mientras la cuenta no tenga dueño (la API lo vuelve a comprobar).
function sameSecret(a: string, b: string): boolean {
  const ha = createHash("sha256").update(a).digest();
  const hb = createHash("sha256").update(b).digest();
  return timingSafeEqual(ha, hb);
}

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as {
    app_password?: string;
    name?: string;
    email?: string;
    password?: string;
    language?: string;
    accept_terms?: boolean;
  };
  const expected = process.env.APP_PASSWORD;
  if (!expected || !body.app_password || !sameSecret(body.app_password, expected)) {
    return relay(401, { detail: "Contraseña actual incorrecta", code: "wrong_app_password" });
  }
  const { status, data } = await callAuth(req, "claim", {
    name: body.name ?? "",
    email: body.email ?? "",
    password: body.password ?? "",
    language: body.language ?? "es",
    kind: kindFor(req),
    accept_terms: body.accept_terms === true,
  });
  if (status === 200 && typeof data.token === "string") return withSession(req, data.token);
  return relay(status, data);
}
