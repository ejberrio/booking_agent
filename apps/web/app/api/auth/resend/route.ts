import { callAuth, relay } from "@/lib/server/auth-api";

export async function POST(req: Request) {
  const { email } = (await req.json().catch(() => ({}))) as { email?: string };
  const { status, data } = await callAuth(req, "resend-verification", { email: email ?? "" });
  return relay(status, data);
}
