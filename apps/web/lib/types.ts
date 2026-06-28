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

export interface Suggestion {
  id: number;
  unit_type_id: number | null;
  date_from: string;
  date_to: string;
  suggested_price: string;
  rationale: { text?: string; event_relevance?: string | null } | null;
  confidence: string | null;
  status: string;
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
