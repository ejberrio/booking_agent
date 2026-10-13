import { NextRequest } from "next/server";
import { callAuth, redirectTo, redirectWithSession } from "@/lib/server/auth-api";

// La app de Android canjea el código de traspaso (Entrar con Google) por su sesión de 90 días.
export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams;
  const { status, data } = await callAuth(req, "handoff", {
    code: q.get("code") ?? "",
    verifier: q.get("verifier") ?? "",
  });
  if (status === 200 && typeof data.token === "string") return redirectWithSession(req, data.token);
  const err = typeof data.code === "string" ? data.code : "google_failed";
  return redirectTo(req, `/login?error=${err}`);
}
