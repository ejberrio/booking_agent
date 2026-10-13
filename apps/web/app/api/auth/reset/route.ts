import { callAuth, relay } from "@/lib/server/auth-api";

export async function POST(req: Request) {
  const { token, password } = (await req.json().catch(() => ({}))) as {
    token?: string;
    password?: string;
  };
  const { status, data } = await callAuth(req, "reset-password", {
    token: token ?? "",
    password: password ?? "",
  });
  return relay(status, data);
}
