"use client";

import Link from "next/link";
import { useI18n } from "@/lib/i18n";

/** Casilla obligatoria de Términos y Privacidad (feature 028). Los enlaces abren aparte. */
export function AcceptTerms({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  const { m } = useI18n();
  const t = m.legal.accept;
  return (
    <label className="flex items-start gap-2 text-xs text-muted-foreground">
      <input
        type="checkbox"
        className="mt-0.5 h-4 w-4 shrink-0 accent-primary"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        required
      />
      <span>
        {t.before}
        <Link href="/terms" target="_blank" className="underline">{t.terms}</Link>
        {t.and}
        <Link href="/privacy" target="_blank" className="underline">{t.privacy}</Link>
        {t.after}
      </span>
    </label>
  );
}
