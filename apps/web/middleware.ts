import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

const PUBLIC = ["/login", "/api/login"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (PUBLIC.some((p) => pathname.startsWith(p))) {
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
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg).*)"],
};
