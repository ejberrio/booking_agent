"use client";

import type { PendingAction } from "@/lib/types";
import { useI18n } from "@/lib/i18n";

function money(v: string | null, lang: string): string {
  if (v === null) return "—";
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString(lang) : v;
}

function range(from: string, to: string, lang: string): string {
  const f = (d: string) =>
    new Date(`${d}T12:00:00`).toLocaleDateString(lang, { day: "numeric", month: "short" });
  return from === to ? f(from) : `${f(from)} – ${f(to)}`;
}

/** Tabla de la propuesta del asistente (feature 032): tramos, antes → después, omitidas. */
export function ActionPreview({ action }: { action: PendingAction }) {
  const { m, lang } = useI18n();
  const t = m.chat.preview;
  const p = action.preview;
  if (!p?.rows?.length) return null;
  const skipped = Object.entries(p.totals?.skipped ?? {}).filter(([, n]) => n > 0);
  const rows = p.rows.slice(0, 12);
  return (
    <div className="space-y-2 rounded-xl border border-border bg-background p-3 text-xs">
      <table className="w-full text-left">
        <thead className="text-muted-foreground">
          <tr>
            <th className="pb-1 pr-2 font-medium">{t.dates}</th>
            <th className="pb-1 pr-2 font-medium">{t.nights}</th>
            <th className="pb-1 pr-2 font-medium">{t.before}</th>
            <th className="pb-1 font-medium">{t.after}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.from}-${r.to}-${r.new}`} className="border-t border-border">
              <td className="py-1 pr-2">{range(r.from, r.to, lang)}</td>
              <td className="py-1 pr-2">{r.nights}</td>
              <td className="py-1 pr-2 text-muted-foreground">{money(r.old, lang)}</td>
              <td className="py-1 font-medium">
                {money(r.new, lang)}
                {r.note && <span className="ml-1 text-muted-foreground">({r.note})</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {p.rows.length > rows.length && (
        <p className="text-muted-foreground">+{p.rows.length - rows.length}…</p>
      )}
      <p className="text-muted-foreground">
        {p.totals ? t.affected(p.totals.affected) : null}
        {p.currency ? ` · ${p.currency}` : ""}
      </p>
      {skipped.length > 0 && (
        <p className="text-muted-foreground">
          {t.skipped}: {skipped.map(([k, n]) => `${n} ${t.reasons[k] ?? k}`).join(", ")}
        </p>
      )}
      {(p.warnings ?? []).map((w) => (
        <p key={w} className="text-amber-600 dark:text-amber-400">⚠️ {w}</p>
      ))}
      {action.reinforced && <p className="text-amber-600 dark:text-amber-400">{t.bigChange}</p>}
    </div>
  );
}
