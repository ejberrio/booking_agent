export interface CalendarDay {
  date: string;
  base_price: string | null;
  effective_price: string | null;
  available: number | null;
  is_blocked: boolean;
  promotions: string[];
}

export type AvailabilityAction = "block" | "open";

export interface AvailabilityDay {
  date: string;
  old_available: number | null;
  new_available: number;
  valid: boolean;
  skip_reason: string | null;
}

export interface AvailabilityPreview {
  items: AvailabilityDay[];
  fingerprint: string;
  affected_count: number;
  skipped_count: number;
  reinforced: boolean;
}

export interface AvailabilityApplyResult {
  applied: string[];
  skipped: [string, string][];
  audited: number;
  published: number;
  publish_issues: number;
  stale: boolean;
}

export interface PreviewDay {
  date: string;
  old_price: string | null;
  new_price: string;
  valid: boolean;
  reason: string | null;
}

export interface ChangePreview {
  items: PreviewDay[];
  fingerprint: string;
  has_invalid: boolean;
  valid_count: number;
  invalid_count: number;
}

export interface ApplyResult {
  applied_days: string[];
  skipped_invalid: string[];
  audited: number;
  published: number;
  publish_issues: number;
  stale: boolean;
}

export interface Promotion {
  id: number;
  name: string;
  offer_id: number | null;
  first_night: string;
  last_night: string;
  base_price: string | null;
  price: string;
  discount_pct: string | null;
  saving: string | null;
  min_nights: number | null;
  status: "published" | "sync_error" | "retired";
  published: boolean;
  channels_scope: string[] | null;
}

export interface PromotionPreview {
  offer_id: number;
  first_night: string;
  last_night: string;
  name: string;
  base_price: string | null;
  price: string;
  discount_pct: string | null;
  saving: string | null;
  min_nights: number | null;
  warnings: string[];
  valid: boolean;
  fingerprint: string;
  channels_scope: string[] | null;
}

export interface PromotionApplyResult {
  id: number | null;
  status: string;
  external_id: number | null;
  published: boolean;
  issue: string | null;
}

export interface SuggestionFactor {
  kind: "event" | "occupancy" | "gap" | "market";
  label: string;
  pct?: number | null;
  event?: {
    name: string;
    location?: string | null;
    dates?: string | null;
    source_url?: string | null;
  };
  // Campos estructurados (feature 021) para componer la frase en el idioma elegido.
  relevance?: "high" | "medium" | "low";
  days?: number;
  adr?: string;
  samples?: number;
  source?: string;
  state?: "used" | "low_confidence" | "discarded";
  weight?: number;
}

export interface Suggestion {
  id: number;
  unit_type_id: number | null;
  date_from: string;
  date_to: string;
  suggested_price: string;
  current_price?: string | null;
  rationale: {
    text?: string;
    event_relevance?: string | null;
    factors?: SuggestionFactor[]; // v2 (feature 018)
    market?: { adr: string; samples: number; source: string };
  } | null;
  confidence: string | null;
  status: string;
  applied_from?: string; // solo en la respuesta de apply (recorte de días pasados)
}

export interface Poi {
  id: number;
  name: string;
  note: string | null;
  date_from: string | null;
  date_to: string | null;
  is_active: boolean;
}

export interface ScanConfigView {
  zone: string | null;
  effective_zone: string;
  queries_per_scan: number;
  event_kinds: string | null;
}

export interface ChatReply {
  reply: string;
  conversation_id: number;
  pending_action_id: number | null;
  applied: boolean;
}

export interface ConnectionStatus {
  status: string;
  account: string | null;
}

export interface RangeSelection {
  date_from: string;
  date_to: string;
  weekdays?: number[] | null;
}

export interface MonthKpis {
  date_from: string;
  date_to: string;
  reserved_nights: Record<"booking" | "airbnb" | "direct", number>;
  total_reserved: number;
  blocked_nights: number;
}

export interface SecretStatus {
  name: string;
  label: string;
  service: string;
  configured: boolean;
  source: "app" | "env" | null;
  hint: string;
  updated_at: string | null;
  unreadable: boolean;
}

export interface SecretAuditEntry {
  name: string;
  action: "set" | "deleted";
  hint: string;
  changed_at: string;
}

export interface SecretTestResult {
  ok: boolean;
  detail: string;
}

// --- Sugerencias accionables (feature 019) ---
export interface SellableNight {
  date: string;
  suggestion_id: number;
  current_price: string | null;
  suggested_price: string;
}

export interface SuggestionView extends Suggestion {
  total_nights: number;
  sellable_count: number;
  occupied_count: number;
}

export interface SuggestionBlock {
  key: string;
  kind: "event" | "period";
  title: string;
  date_from: string;
  date_to: string;
  direction: "up" | "down" | "mixed";
  suggestion_ids: number[];
  nights: SellableNight[];
  suggestions: SuggestionView[];
}

export interface BatchPreviewItem {
  date: string;
  suggestion_id: number;
  old_price: string | null;
  new_price: string;
  valid: boolean;
  reason: string | null;
}

export interface BatchPreview {
  suggestion_ids: number[];
  items: BatchPreviewItem[];
  valid_count: number;
  skipped_count: number;
  fingerprint: string;
}

export interface BatchResult {
  nights: { date: string; suggestion_id: number; status: "applied" | "skipped" | "failed"; reason: string | null }[];
  applied_count: number;
  skipped_count: number;
  failed_count: number;
  suggestions: Record<string, "applied" | "pending" | "unchanged">;
}

export interface BookingView {
  id: number;
  guest_name: string | null;
  channel: string;
  check_in: string;
  check_out: string;
  nights: number;
  status: string;
  external_ref: string | null;
}

export interface CalendarNote {
  id: number;
  unit_type_id: number;
  date_from: string;
  date_to: string;
  text: string;
}

export interface NativeDeal {
  id: number;
  channel: "booking" | "airbnb";
  name: string;
  discount_pct: string;
  date_from: string | null;
  date_to: string | null;
  is_active: boolean;
}

export interface NativeDealInput {
  channel: "booking" | "airbnb";
  name: string;
  discount_pct: number;
  date_from?: string | null;
  date_to?: string | null;
  is_active?: boolean;
}

export interface ChannelStatus {
  kind: "booking" | "airbnb" | "direct";
  is_active: boolean;
  bookings: number;
}

export interface SystemStatus {
  version: string;
  environment: string;
  db: string;
  beds24: string;
  open_issues: number;
  channels: ChannelStatus[];
}

export interface ChannelOffset {
  channel: "booking" | "airbnb";
  offset_pct: number | null;
  supported: boolean;
  is_active: boolean;
}

export interface OffsetPreview {
  channel: string;
  current_pct: string | null;
  new_pct: string;
  example: { base: string; effective: string };
  warnings: string[];
  fingerprint: string;
}

export interface OffsetApplyResult {
  applied: boolean;
  verified: boolean;
  channel: string;
  offset_pct: number;
  issue: string | null;
}

// --- Reservas en tiempo real (feature 020) ---
export interface WebhookStatus {
  configured: boolean;
  status: "unconfigured" | "never" | "active" | "idle";
  last_accepted_at: string | null;
  counts_7d: { accepted: number; ignored: number; rejected: number; failed: number };
  endpoint_url: string;
  header_name: string;
}
