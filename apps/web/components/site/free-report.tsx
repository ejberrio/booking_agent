"use client";

import Link from "next/link";
import { useState } from "react";
import { FormNote } from "@/components/auth/auth-shell";
import { type Municipality, MunicipalityPicker } from "@/components/site/municipality-picker";
import { WaitlistForm } from "@/components/site/waitlist-form";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatCOP } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { LOCALE, type Lang } from "@/lib/i18n/core";

export type ReportEvent = {
  name: string;
  start_date: string;
  end_date: string;
  relevance: "high" | "medium" | "low";
  kind: string;
  location: string | null;
  base_price: string;
  suggested_price: string;
  pct: number;
};

type ReportResponse = {
  token: string;
  municipality: Municipality;
  status: "ok" | "no_events" | "budget_exhausted";
  events: ReportEvent[];
  total_events: number;
  registration: { open: boolean; full: boolean };
};

export const REPORT_KEY = "sl_report";

export function formatDates(ev: { start_date: string; end_date: string }, lang: Lang): string {
  const f = new Intl.DateTimeFormat(LOCALE[lang], { weekday: "short", day: "numeric", month: "short" });
  const d = (s: string) => f.format(new Date(`${s}T12:00:00`));
  return ev.end_date && ev.end_date !== ev.start_date ? `${d(ev.start_date)} – ${d(ev.end_date)}` : d(ev.start_date);
}

const REL_STYLE = {
  high: "bg-red-500/15 text-red-600 dark:text-red-400",
  medium: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  low: "bg-sky-500/15 text-sky-700 dark:text-sky-400",
};

export function EventRow({ ev }: { ev: ReportEvent }) {
  const { m, lang } = useI18n();
  const t = m.pub.report;
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-3">
      <div className="min-w-0 space-y-1">
        <p className="text-xs text-muted-foreground">{formatDates(ev, lang)}</p>
        <p className="font-medium leading-snug">{ev.name}</p>
        <span className={`inline-block rounded px-1.5 py-0.5 text-[11px] ${REL_STYLE[ev.relevance]}`}>
          {t.rel[ev.relevance]}
        </span>
      </div>
      <div className="text-right">
        <p className="text-xs text-muted-foreground">{t.suggested}</p>
        <p className="text-lg font-semibold">
          {formatCOP(ev.suggested_price, lang)}
          {ev.pct > 0 && <span className="ml-1 text-xs font-medium text-emerald-600">+{ev.pct}%</span>}
        </p>
        <p className="text-xs text-muted-foreground">{t.from(formatCOP(ev.base_price, lang))}</p>
      </div>
    </li>
  );
}

/** Informe gratis de la página pública (feature 030). */
export function FreeReport() {
  const { m, lang } = useI18n();
  const t = m.pub.report;
  const [muni, setMuni] = useState<Municipality | null>(null);
  const [weekday, setWeekday] = useState("");
  const [weekend, setWeekend] = useState("");
  const [kind, setKind] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [res, setRes] = useState<ReportResponse | null>(null);
  const num = (v: string) => Number(v.replace(/[^\d]/g, "")) || 0;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!muni) return;
    setBusy(true);
    setError(null);
    const r = await fetch("/api/public/report", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        municipality_code: muni.code,
        weekday_price: num(weekday),
        weekend_price: num(weekend) || null,
        unit_kind: kind || null,
        language: lang,
      }),
    }).catch(() => null);
    setBusy(false);
    if (!r) return setError(t.error);
    if (r.status === 429) return setError(t.limited);
    if (!r.ok) return setError(t.error);
    const data = (await r.json()) as ReportResponse;
    try {
      sessionStorage.setItem(REPORT_KEY, data.token);
    } catch {
      // sin almacenamiento: el enlace de registro lleva el informe igual
    }
    setRes(data);
  }

  if (res) {
    const more = res.total_events - res.events.length;
    return (
      <Card className="space-y-4">
        <h3 className="text-lg font-semibold">{t.resultTitle(res.municipality.label)}</h3>
        {res.events.length > 0 ? (
          <ul className="divide-y divide-border">
            {res.events.map((ev) => <EventRow key={`${ev.name}-${ev.start_date}`} ev={ev} />)}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">{res.status === "budget_exhausted" ? t.budget : t.none}</p>
        )}
        {more > 0 && <p className="text-sm font-medium">{t.more(more)}</p>}
        <p className="text-xs text-muted-foreground">{t.disclaimer}</p>
        {res.registration.full ? (
          <WaitlistForm municipalityCode={res.municipality.code} />
        ) : (
          <div className="space-y-2">
            <Link href={`/register?report=${encodeURIComponent(res.token)}`}
              className="block rounded-md bg-primary px-4 py-2.5 text-center text-sm font-medium text-primary-foreground">
              {t.full}
            </Link>
            <p className="text-center text-xs text-muted-foreground">{t.fullHint}</p>
          </div>
        )}
        <button type="button" onClick={() => setRes(null)} className="text-sm text-muted-foreground underline">
          {t.again}
        </button>
      </Card>
    );
  }

  return (
    <Card className="space-y-3">
      <form onSubmit={submit} className="space-y-3">
        <label className="block space-y-1 text-sm">
          <span>{t.municipality}</span>
          <MunicipalityPicker value={muni} onChange={setMuni} />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block space-y-1 text-sm">
            <span>{t.weekday}</span>
            <Input inputMode="numeric" placeholder="250.000" value={weekday}
              onChange={(e) => setWeekday(e.target.value)} required />
          </label>
          <label className="block space-y-1 text-sm">
            <span>{t.weekend}</span>
            <Input inputMode="numeric" placeholder="300.000" value={weekend}
              onChange={(e) => setWeekend(e.target.value)} />
          </label>
        </div>
        <label className="block space-y-1 text-sm">
          <span>{t.unitKind}</span>
          <select value={kind} onChange={(e) => setKind(e.target.value)}
            className="h-9 w-full rounded-md border border-border bg-background px-2 text-sm">
            <option value="">—</option>
            {Object.entries(t.unitKinds).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
        </label>
        {error && <FormNote kind="error">{error}</FormNote>}
        {busy && <p className="text-xs text-muted-foreground">{t.loading}</p>}
        <Button type="submit" className="w-full" disabled={busy || !muni || num(weekday) <= 0}>
          {t.submit}
        </Button>
      </form>
    </Card>
  );
}
