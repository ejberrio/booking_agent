import { callAuth, relay } from "@/lib/server/auth-api";

export async function GET(req: Request) {
  const { status, data } = await callAuth(req, "registration-status", undefined, "GET");
  return relay(status, data);
}

export const dynamic = "force-dynamic";
