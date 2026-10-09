import { NextResponse } from "next/server";
import { SESSION_COOKIE, createSessionToken, sessionMaxAgeFor } from "@/lib/session";

export async function POST(request: Request) {
  const { password } = (await request.json()) as { password?: string };
  const expected = process.env.APP_PASSWORD;

  if (!expected) {
    return NextResponse.json(
      { error: "APP_PASSWORD no configurada en el servidor" },
      { status: 500 },
    );
  }
  if (password !== expected) {
    return NextResponse.json({ error: "Contraseña incorrecta" }, { status: 401 });
  }

  // En la app móvil la sesión dura 90 días; en el navegador, 7 (feature 025).
  const maxAge = sessionMaxAgeFor(request.headers.get("user-agent"));
  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, await createSessionToken(expected, Date.now(), maxAge), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge,
    secure: process.env.NODE_ENV === "production",
  });
  return res;
}
