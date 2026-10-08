import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

const PUBLIC = ["/login", "/api/login", "/api/hooks/"]; // hooks: avisos de Beds24 (auth por clave propia)

export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  // Dominio canónico sin "www": redirección permanente conservando ruta y query.
  const host = request.headers.get("host") ?? "";
  if (host.startsWith("www.")) {
    return NextResponse.redirect(`https://${host.slice(4)}${pathname}${search}`, 308);
  }
  if (PUBLIC.some((p) => pathname.startsWith(p)) || pathname === "/icon.svg") {
    return NextResponse.next();
  }
  // La cookie debe llevar una firma válida y vigente: su mera presencia no basta.
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!(await verifySessionToken(token, process.env.APP_PASSWORD))) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // Protege todo excepto assets estáticos.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
