import { getActiveLang } from "@/lib/i18n/core";
import { trServer } from "@/lib/i18n/server-messages";
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
  BookingView,
  BatchPreview,
  BatchResult,
  WebhookStatus,
  SuggestionBlock,
  CalendarNote,
  SecretAuditEntry,
  SecretStatus,
  SecretTestResult,
  ChannelOffset,
  MonthKpis,
  NativeDeal,
  NativeDealInput,
  Poi,
  ScanConfigView,
  OffsetApplyResult,
  OffsetPreview,
  RangeSelection,
  Suggestion,
  SystemStatus,
  HorizonStatus,
  ExtensionParams,
  ExtensionPreview,
  ExtensionResult,
  ConversationSummary,
  ConversationDetail,
  PushDevice,
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
  channels_scope?: string[] | null;
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
  if (!res.ok) {
    // El backend responde errores honestos en `detail` (p. ej. estado real de una
    // sugerencia ya resuelta): se propaga para mostrarlo tal cual.
    const detail = await res
      .json()
      .then((b) => (typeof b?.detail === "string" ? b.detail : null))
      .catch(() => null);
    // Traducido al idioma activo en UN solo punto (feature 021); sin traducción → español.
    throw new Error(trServer(detail ?? `API ${res.status} en ${path}`));
  }
  return (await res.json()) as T;
}

export const api = {
  // Pricing
  getCalendar: (unitTypeId: number, from: string, to: string) =>
    req<CalendarDay[]>(
      `/pricing/calendar?unit_type_id=${unitTypeId}&date_from=${from}&date_to=${to}`,
    ),
  getKpis: (unitTypeId: number, from: string, to: string) =>
    req<MonthKpis>(`/pricing/kpis?unit_type_id=${unitTypeId}&date_from=${from}&date_to=${to}`),
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
  listPendingSuggestions: () => req<Suggestion[]>(`/suggestions?pending=true`),
  // Feature 019: bloques vendibles y aplicación en lote (una vista previa + una confirmación)
  listSuggestionBlocks: () =>
    req<{ blocks: SuggestionBlock[]; hidden_occupied: number }>(`/suggestions/blocks`),
  previewSuggestionBatch: (suggestion_ids: number[]) =>
    req<BatchPreview>(`/suggestions/batch/preview`, {
      method: "POST",
      body: JSON.stringify({ suggestion_ids }),
    }),
  applySuggestionBatch: (suggestion_ids: number[], fingerprint: string) =>
    req<BatchResult>(`/suggestions/batch/apply`, {
      method: "POST",
      body: JSON.stringify({ suggestion_ids, fingerprint }),
    }),
  rejectSuggestion: (id: number) =>
    req<Suggestion>(`/suggestions/${id}/reject`, { method: "POST" }),
  applySuggestion: (id: number) =>
    req<Suggestion>(`/suggestions/${id}/apply`, { method: "POST" }),

  // Promociones (ofertas con descuento sobre fechas, feature 011)
  // POIs y configuración del scan (feature 018)
  listPois: () => req<{ pois: Poi[] }>(`/pois`),
  createPoi: (body: { name: string; note?: string | null; date_from?: string | null; date_to?: string | null }) =>
    req<Poi>(`/pois`, { method: "POST", body: JSON.stringify(body) }),
  updatePoi: (id: number, body: Partial<Omit<Poi, "id">>) =>
    req<Poi>(`/pois/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deletePoi: (id: number) => req<{ deleted: boolean }>(`/pois/${id}`, { method: "DELETE" }),
  getScanConfig: () => req<ScanConfigView>(`/scan-config`),
  updateScanConfig: (body: { zone?: string | null; queries_per_scan?: number; event_kinds?: string | null }) =>
    req<ScanConfigView>(`/scan-config`, { method: "PUT", body: JSON.stringify(body) }),

  // Secretos (feature 017): write-only, los valores nunca vuelven
  listSecrets: () => req<{ secrets: SecretStatus[] }>(`/settings/secrets`),
  setSecret: (name: string, value: string) =>
    req<SecretStatus>(`/settings/secrets/${name}`, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
  deleteSecret: (name: string) =>
    req<SecretStatus>(`/settings/secrets/${name}`, { method: "DELETE" }),
  redeemBeds24Invite: (code: string) =>
    req<SecretStatus>(`/settings/secrets/beds24_refresh_token/invite`, {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  testSecret: (name: string) =>
    req<SecretTestResult>(`/settings/secrets/${name}/test`, { method: "POST" }),
  listSecretAudit: () => req<{ entries: SecretAuditEntry[] }>(`/settings/secrets/audit`),

  // Reservas (lectura) y notas del host (feature 016)
  listBookings: (unitTypeId: number, from: string, to: string) =>
    req<{ bookings: BookingView[] }>(
      `/bookings?unit_type_id=${unitTypeId}&date_from=${from}&date_to=${to}`,
    ),
  listCalendarNotes: (unitTypeId: number) =>
    req<{ notes: CalendarNote[] }>(`/calendar-notes?unit_type_id=${unitTypeId}`),
  createCalendarNote: (body: { unit_type_id: number; date_from: string; date_to: string; text: string }) =>
    req<CalendarNote>(`/calendar-notes`, { method: "POST", body: JSON.stringify(body) }),
  updateCalendarNote: (id: number, body: { text?: string; date_from?: string; date_to?: string }) =>
    req<CalendarNote>(`/calendar-notes/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteCalendarNote: (id: number) =>
    req<{ deleted: boolean }>(`/calendar-notes/${id}`, { method: "DELETE" }),

  // Precio mínimo por noche (feature 022): piso de las promociones de sugerencias
  // Extender precios (feature 023)
  getHorizonStatus: (unitTypeId: number) =>
    req<HorizonStatus>(`/pricing/extension/status?unit_type_id=${unitTypeId}`),
  previewExtension: (params: ExtensionParams) =>
    req<ExtensionPreview>(`/pricing/extension/preview`, {
      method: "POST",
      body: JSON.stringify(params),
    }),
  applyExtension: (params: ExtensionParams, fingerprint: string) =>
    req<ExtensionResult>(`/pricing/extension/apply`, {
      method: "POST",
      body: JSON.stringify({ ...params, fingerprint }),
    }),

  getMinPrice: () => req<{ min_price: string | null }>(`/pricing/min-price`),
  putMinPrice: (min_price: number | null) =>
    req<{ min_price: string | null }>(`/pricing/min-price`, {
      method: "PUT",
      body: JSON.stringify({ min_price }),
    }),

  // Deals nativos (feature 015: registro informativo local)
  listNativeDeals: () => req<{ deals: NativeDeal[] }>(`/pricing/native-deals`),
  createNativeDeal: (body: NativeDealInput) =>
    req<NativeDeal>(`/pricing/native-deals`, { method: "POST", body: JSON.stringify(body) }),
  updateNativeDeal: (id: number, body: Partial<NativeDealInput>) =>
    req<NativeDeal>(`/pricing/native-deals/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteNativeDeal: (id: number) =>
    req<{ deleted: boolean }>(`/pricing/native-deals/${id}`, { method: "DELETE" }),

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
  // Avisos al celular (feature 025)
  registerPushDevice: (body: { token: string; platform: "android" | "ios"; model?: string; app_version?: string }) =>
    req<PushDevice>(`/push/devices`, { method: "POST", body: JSON.stringify(body) }),
  listPushDevices: () => req<PushDevice[]>(`/push/devices`),
  updatePushDevice: (id: number, body: { notify_bookings?: boolean; notify_suggestions?: boolean }) =>
    req<PushDevice>(`/push/devices/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deletePushDevice: (id: number) => req<{ deleted: boolean }>(`/push/devices/${id}`, { method: "DELETE" }),
  pushStatus: () => req<{ configured: boolean; devices: number }>(`/push/status`),
  testPush: () => req<{ sent: number; failed: number; configured: boolean }>(`/push/test`, { method: "POST" }),

  // Historial de chat (feature 024)
  listConversations: (limit = 20) => req<ConversationSummary[]>(`/chat/conversations?limit=${limit}`),
  getConversation: (id: number) => req<ConversationDetail>(`/chat/conversations/${id}`),
  chat: (message: string, conversationId?: number) =>
    req<ChatReply>(`/chat`, {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? null,
        language: getActiveLang(), // feature 021: el asistente responde en el idioma activo
      }),
    }),

  // Estado del sistema (incluye canales conectados y reservas por canal)
  getStatus: () => req<SystemStatus>(`/status`),

  // Preferencias del host (feature 021): idioma para todos sus dispositivos
  getPreferences: () => req<{ language: "es" | "en" | "pt" }>(`/preferences`),
  putPreferences: (language: "es" | "en" | "pt") =>
    req<{ language: "es" | "en" | "pt" }>(`/preferences`, {
      method: "PUT",
      body: JSON.stringify({ language }),
    }),

  // Ajuste de precio por canal (feature 013)
  getChannelOffsets: () => req<{ offsets: ChannelOffset[] }>(`/pricing/channel-offsets`),
  previewChannelOffset: (body: { channel: string; offset_pct: number }) =>
    req<OffsetPreview>(`/pricing/channel-offsets/preview`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  applyChannelOffset: (body: { channel: string; offset_pct: number; fingerprint: string }) =>
    req<OffsetApplyResult>(`/pricing/channel-offsets/apply`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Reservas en tiempo real (feature 020): estado y clave (la línea se ve UNA vez)
  getWebhookStatus: () => req<WebhookStatus>(`/hooks/beds24/status`),
  generateWebhookKey: () =>
    req<{ header_line: string; hint: string }>(`/hooks/beds24/key`, { method: "POST" }),

  // Sync
  testConnection: () => req<ConnectionStatus>(`/sync/test`, { method: "POST" }),
  importRemote: (days = 730) =>
    req<{ run_id: number; status: string; created: number; updated: number; issues: number }>(`/sync/import`, {
      method: "POST",
      body: JSON.stringify({ days }),
    }),
};
