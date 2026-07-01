import type {
  ApplyResult,
  AvailabilityAction,
  AvailabilityApplyResult,
  AvailabilityPreview,
  CalendarDay,
  ChangePreview,
  ChatReply,
  ConnectionStatus,
  Promotion,
  PromotionApplyResult,
  PromotionPreview,
  RangeSelection,
  Suggestion,
} from "@/lib/types";

export interface PromotionInput {
  unit_type_id: number;
  first_night: string;
  last_night: string;
  name: string;
  discount_pct?: number | null;
  price?: number | null;
  min_nights?: number | null;
  promotion_id?: number | null;
}

// Las llamadas van al proxy server-side de la propia web (mismo origen).
// El navegador nunca habla con la API directamente; el proxy reenvía a la API privada.
// `lib/sse.ts` también usa esta constante (chat SSE → /api/proxy/chat/stream).
export const API_URL = "/api/proxy";

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

  // Disponibilidad (bloquear/abrir)
  availabilityPreview: (body: {
    unit_type_id: number;
    action: AvailabilityAction;
    selection: RangeSelection;
  }) =>
    req<AvailabilityPreview>(`/pricing/availability/preview`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  availabilityApply: (body: {
    unit_type_id: number;
    action: AvailabilityAction;
    selection: RangeSelection;
    fingerprint: string;
  }) =>
    req<AvailabilityApplyResult>(`/pricing/availability/apply`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Suggestions
  listSuggestions: (status?: string) =>
    req<Suggestion[]>(`/suggestions${status ? `?status=${status}` : ""}`),
  approveSuggestion: (id: number) =>
    req<Suggestion>(`/suggestions/${id}/approve`, { method: "POST" }),
  rejectSuggestion: (id: number) =>
    req<Suggestion>(`/suggestions/${id}/reject`, { method: "POST" }),
  applySuggestion: (id: number) =>
    req<Suggestion>(`/suggestions/${id}/apply`, { method: "POST" }),

  // Promociones (ofertas con descuento sobre fechas, feature 011)
  listPromotions: (unitTypeId: number) =>
    req<{ promotions: Promotion[] }>(`/pricing/promotions?unit_type_id=${unitTypeId}`),
  previewPromotion: (body: PromotionInput) =>
    req<PromotionPreview>(`/pricing/promotions/preview`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  applyPromotion: (body: PromotionInput & { fingerprint: string; confirm_overlap?: boolean }) =>
    req<PromotionApplyResult>(`/pricing/promotions/apply`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  retirePromotion: (id: number) =>
    req<PromotionApplyResult>(`/pricing/promotions/retire`, {
      method: "POST",
      body: JSON.stringify({ id, confirm: true }),
    }),

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
