import { NextResponse } from "next/server";
import { SESSION_COOKIE, SESSION_MAX_AGE, createSessionToken } from "@/lib/session";

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

  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, await createSessionToken(expected), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE,
    secure: process.env.NODE_ENV === "production",
  });
  return res;
}
