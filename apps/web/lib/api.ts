import type {
  ApplyResult,
  CalendarDay,
  ChangePreview,
  ChatReply,
  ConnectionStatus,
  RangeSelection,
  Suggestion,
} from "@/lib/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) throw new Error(`API ${res.status} en ${path}`);
  return (await res.json()) as T;
}

export const api = {
  // Pricing
  getCalendar: (unitTypeId: number, from: string, to: string) =>
    req<CalendarDay[]>(
      `/pricing/calendar?unit_type_id=${unitTypeId}&date_from=${from}&date_to=${to}`,
    ),
  previewRange: (body: { unit_type_id: number; selection: RangeSelection; price: number }) =>
    req<ChangePreview>(`/pricing/range/preview`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  applyRange: (body: {
    unit_type_id: number;
    selection: RangeSelection;
    price: number;
    fingerprint: string;
  }) =>
    req<ApplyResult>(`/pricing/range/apply`, { method: "POST", body: JSON.stringify(body) }),

  // Suggestions
  listSuggestions: (status?: string) =>
    req<Suggestion[]>(`/suggestions${status ? `?status=${status}` : ""}`),
  approveSuggestion: (id: number) =>
    req<Suggestion>(`/suggestions/${id}/approve`, { method: "POST" }),
  rejectSuggestion: (id: number) =>
    req<Suggestion>(`/suggestions/${id}/reject`, { method: "POST" }),
  applySuggestion: (id: number) =>
    req<Suggestion>(`/suggestions/${id}/apply`, { method: "POST" }),

  // Chat (no streaming)
  chat: (message: string, conversationId?: number) =>
    req<ChatReply>(`/chat`, {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversationId ?? null }),
    }),

  // Sync
  testConnection: () => req<ConnectionStatus>(`/sync/test`, { method: "POST" }),
  importRemote: (days = 365) =>
    req<{ run_id: number; status: string; created: number; issues: number }>(`/sync/import`, {
      method: "POST",
      body: JSON.stringify({ days }),
    }),
};
