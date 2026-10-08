"use client";

import { formatNumber } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Messages } from "@/lib/i18n/messages";
import type { Suggestion, SuggestionFactor } from "@/lib/types";

function signedPct(pct: number): string {
  const n = Math.round(pct);
  return n >= 0 ? `+${n}%` : `−${Math.abs(n)}%`;
}

/** Frase del factor en el idioma activo desde sus campos estructurados (feature 021).
 *  Datos viejos sin estructura → `label` (español, idioma de referencia). */
function factorText(f: SuggestionFactor, r: Messages["rationale"]): string {
  if (f.kind === "event" && f.event?.name && f.relevance && f.pct != null) {
    return r.event(f.event.name, r.relevance[f.relevance] ?? f.relevance, signedPct(f.pct));
  }
  if (f.kind === "occupancy" && f.pct != null) return r.occupancy(signedPct(f.pct));
  if (f.kind === "gap" && f.days != null && f.pct != null) return r.gap(f.days, signedPct(f.pct));
  if (f.kind === "market" && f.adr && f.state) {
    const adr = formatNumber(Number(f.adr));
    if (f.state === "used") return r.marketUsed(adr, f.samples ?? 0, Math.round((f.weight ?? 0) * 100));
    if (f.state === "low_confidence") return r.marketLow(adr, f.samples ?? 0);
    return r.marketDiscarded(adr);
  }
  return f.label;
}

/** Racional explicable (feature 018): factores con %, evento con lugar y fuente.
 *  Fallback al texto plano para sugerencias v1. */
export function Rationale({ rationale }: { rationale: Suggestion["rationale"] }) {
  const { m } = useI18n();
  if (!rationale) return null;
  const factors = rationale.factors;
  if (!factors?.length) {
    return rationale.text ? <p className="text-xs">{rationale.text}</p> : null;
  }
  return (
    <div className="space-y-1">
      {factors.map((f, i) => {
        const text = factorText(f, m.rationale);
        return (
          <div key={i} className="flex items-start gap-1.5 text-xs">
            <span
              className={`mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
                f.pct == null
                  ? "bg-sky-500"
                  : f.pct >= 0
                    ? "bg-emerald-500"
                    : "bg-orange-500"
              }`}
            />
            <span>
              {text}
              {f.event?.source_url && (
                <>
                  {" "}
                  <a
                    href={f.event.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground underline"
                  >
                    {m.rationale.source}
                  </a>
                </>
              )}
              {f.event?.location && !text.includes(f.event.location) && (
                <span className="text-muted-foreground"> · {f.event.location}</span>
              )}
              {f.event?.dates && (
                <span className="text-muted-foreground"> · {f.event.dates}</span>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
