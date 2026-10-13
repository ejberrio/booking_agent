import { callAuth, clientIp, kindFor, relay, withSession } from "@/lib/server/auth-api";

export async function POST(req: Request) {
  const { email, password } = (await req.json().catch(() => ({}))) as {
    email?: string;
    password?: string;
  };
  const { status, data } = await callAuth(req, "login", {
    email: email ?? "",
    password: password ?? "",
    kind: kindFor(req),
    ip: clientIp(req),
  });
  if (status === 200 && typeof data.token === "string") return withSession(req, data.token);
  return relay(status, data);
}
