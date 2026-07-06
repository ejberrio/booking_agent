"use client";

import type { Suggestion } from "@/lib/types";

/** Racional explicable v2 (feature 018): factores con %, evento con lugar y fuente.
 *  Fallback al texto plano para sugerencias v1. */
export function Rationale({ rationale }: { rationale: Suggestion["rationale"] }) {
  if (!rationale) return null;
  const factors = rationale.factors;
  if (!factors?.length) {
    return rationale.text ? <p className="text-xs">{rationale.text}</p> : null;
  }
  return (
    <div className="space-y-1">
      {factors.map((f, i) => (
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
            {f.label}
            {f.event?.source_url && (
              <>
                {" "}
                <a
                  href={f.event.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted-foreground underline"
                >
                  fuente
                </a>
              </>
            )}
            {f.event?.location && !f.label.includes(f.event.location) && (
              <span className="text-muted-foreground"> · {f.event.location}</span>
            )}
            {f.event?.dates && (
              <span className="text-muted-foreground"> · {f.event.dates}</span>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
