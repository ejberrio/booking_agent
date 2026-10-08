import { getActiveLang, LOCALE, type Lang } from "@/lib/i18n/core";

// Formatos según el idioma ACTIVO (feature 021). La moneda es siempre COP.
const copCache = new Map<string, Intl.NumberFormat>();

function locale(lang?: Lang): string {
  return LOCALE[lang ?? getActiveLang()];
}

function cop(lang?: Lang): Intl.NumberFormat {
  const loc = locale(lang);
  let f = copCache.get(loc);
  if (!f) {
    f = new Intl.NumberFormat(loc, { style: "currency", currency: "COP", maximumFractionDigits: 0 });
    copCache.set(loc, f);
  }
  return f;
}

export function formatCOP(value: string | number | null | undefined, lang?: Lang): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return "—";
  return cop(lang).format(n);
}

export function formatNumber(value: number, lang?: Lang): string {
  return new Intl.NumberFormat(locale(lang)).format(value);
}

export function ymd(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function monthRange(year: number, month: number): { from: string; to: string } {
  const first = new Date(Date.UTC(year, month, 1));
  const last = new Date(Date.UTC(year, month + 1, 0));
  return { from: ymd(first), to: ymd(last) };
}

export function monthLabel(year: number, month: number, lang?: Lang): string {
  const s = new Intl.DateTimeFormat(locale(lang), { month: "long", year: "numeric" }).format(
    new Date(year, month, 1),
  );
  // Solo la primera letra en mayúscula ("Outubro de 2026", no "Outubro De 2026").
  return s.charAt(0).toLocaleUpperCase(locale(lang)) + s.slice(1);
}

/** Nombres cortos de los días, lunes primero ("lun.", "Mon", "seg."). */
export function weekdayShortNames(lang?: Lang): string[] {
  const f = new Intl.DateTimeFormat(locale(lang), { weekday: "short", timeZone: "UTC" });
  // 2024-01-01 fue lunes.
  return Array.from({ length: 7 }, (_, i) => f.format(new Date(Date.UTC(2024, 0, 1 + i))));
}

function monthShort(m: number, lang?: Lang): string {
  return new Intl.DateTimeFormat(locale(lang), { month: "short", timeZone: "UTC" })
    .format(new Date(Date.UTC(2024, m - 1, 1)))
    .replace(".", "");
}

/** "2026-11-14" → "14 nov" / "Nov 14" (sin depender de la zona horaria del navegador). */
export function shortDate(iso: string, lang?: Lang): string {
  const [, m, d] = iso.split("-").map(Number);
  const l = lang ?? getActiveLang();
  return l === "en" ? `${monthShort(m, l)} ${d}` : `${d} ${monthShort(m, l)}`;
}

/** Rango compacto: "14–16 nov" / "Nov 14–16", o con dos meses "30 nov – 2 dic". */
export function shortRange(from: string, to: string, lang?: Lang): string {
  if (from === to) return shortDate(from, lang);
  const l = lang ?? getActiveLang();
  const [, mf, df] = from.split("-").map(Number);
  const [, mt, dt] = to.split("-").map(Number);
  if (mf !== mt) return `${shortDate(from, l)} – ${shortDate(to, l)}`;
  return l === "en" ? `${monthShort(mt, l)} ${df}–${dt}` : `${df}–${dt} ${monthShort(mt, l)}`;
}

/** Fecha y hora local legible según el idioma. */
export function dateTime(iso: string, lang?: Lang): string {
  return new Date(iso).toLocaleString(locale(lang));
}

/** Variación porcentual redondeada con signo ("+30%", "−11%"), o "" si no aplica. */
export function pctChange(from: string | null, to: string): string {
  if (!from) return "";
  const a = Number(from);
  const b = Number(to);
  if (!a || Number.isNaN(a) || Number.isNaN(b) || a === b) return "";
  const p = Math.round(((b - a) / a) * 100);
  return p > 0 ? `+${p}%` : `−${Math.abs(p)}%`;
}
