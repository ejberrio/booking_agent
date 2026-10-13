import { callAuth, relay } from "@/lib/server/auth-api";

export async function POST(req: Request) {
  const { email, language } = (await req.json().catch(() => ({}))) as {
    email?: string;
    language?: string;
  };
  const { status, data } = await callAuth(req, "forgot-password", {
    email: email ?? "",
    language,
  });
  return relay(status, data);
}
