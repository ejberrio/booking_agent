import { callAuth, relay } from "@/lib/server/auth-api";

// ¿Qué formas de entrar hay? Hoy: Google, solo si el administrador cargó sus credenciales.
export async function GET(req: Request) {
  const { status, data } = await callAuth(req, "providers", undefined, "GET");
  return relay(status, status === 200 ? data : { google: false });
}
