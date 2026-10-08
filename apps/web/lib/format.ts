const COP = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

export function formatCOP(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) return "—";
  return COP.format(n);
}

export function ymd(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function monthRange(year: number, month: number): { from: string; to: string } {
  const first = new Date(Date.UTC(year, month, 1));
  const last = new Date(Date.UTC(year, month + 1, 0));
  return { from: ymd(first), to: ymd(last) };
}

export function monthLabel(year: number, month: number): string {
  return new Intl.DateTimeFormat("es-CO", { month: "long", year: "numeric" }).format(
    new Date(year, month, 1),
  );
}

const SHORT_MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/** "2026-11-14" → "14 nov" (sin depender de la zona horaria del navegador). */
export function shortDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${d} ${SHORT_MONTHS[m - 1]}`;
}

/** Rango compacto: "14–16 nov", "30 nov – 2 dic" o "14 nov". */
export function shortRange(from: string, to: string): string {
  if (from === to) return shortDate(from);
  const [, mf, df] = from.split("-").map(Number);
  const [, mt, dt] = to.split("-").map(Number);
  return mf === mt ? `${df}–${dt} ${SHORT_MONTHS[mt - 1]}` : `${shortDate(from)} – ${shortDate(to)}`;
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
