import { callAuth, kindFor, relay, withSession } from "@/lib/server/auth-api";

export async function POST(req: Request) {
  const { token } = (await req.json().catch(() => ({}))) as { token?: string };
  const { status, data } = await callAuth(req, "verify-email", {
    token: token ?? "",
    kind: kindFor(req),
  });
  if (status === 200 && typeof data.token === "string") return withSession(req, data.token);
  return relay(status, data);
}
