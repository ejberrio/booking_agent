export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function sendChat(message: string): Promise<string> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`API respondió ${res.status}`);
  const data = (await res.json()) as { reply: string };
  return data.reply;
}
