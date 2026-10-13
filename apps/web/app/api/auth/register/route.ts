import { callAuth, relay } from "@/lib/server/auth-api";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as {
    name?: string;
    email?: string;
    password?: string;
    invite_code?: string;
    language?: string;
  };
  const { status, data } = await callAuth(req, "register", {
    name: body.name ?? "",
    email: body.email ?? "",
    password: body.password ?? "",
    invite_code: body.invite_code || null,
    language: body.language ?? "es",
  });
  return relay(status, data);
}
