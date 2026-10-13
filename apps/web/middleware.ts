import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE, looksLikeSessionToken } from "@/lib/session";

// Páginas y rutas sin sesión (feature 026). hooks: avisos de Beds24 (auth por clave propia).
const PUBLIC = [
  "/login",
  "/claim",
  "/forgot",
  "/reset",
  "/verify",
  "/api/auth/",
  "/api/hooks/",
];

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
  // La API valida la sesión en cada petición; aquí basta con que exista y tenga forma.
  if (!looksLikeSessionToken(request.cookies.get(SESSION_COOKIE)?.value)) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ detail: "Sesión no válida" }, { status: 401 });
    }
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = pathname === "/" ? "" : `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // Protege todo excepto assets estáticos.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
