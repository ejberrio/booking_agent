import { NextRequest, NextResponse } from "next/server";
import { LEGACY_COOKIE, SESSION_COOKIE } from "@/lib/session";

// Cierra la sesión en el SERVIDOR (no solo borra la cookie) y limpia las cookies.
const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const token = req.cookies.get(SESSION_COOKIE)?.value;
  if (token) {
    await fetch(`${API}/auth/logout`, {
      method: "POST",
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    }).catch(() => null);
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, "", { path: "/", maxAge: 0 });
  res.cookies.set(LEGACY_COOKIE, "", { path: "/", maxAge: 0 });
  return res;
}
