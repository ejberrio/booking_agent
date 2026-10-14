"use client";

import { useState } from "react";
import { LegalDialog } from "@/components/legal/legal-dialog";
import type { LegalKind } from "@/components/legal/legal-doc";
import { useI18n } from "@/lib/i18n";

/** Casilla obligatoria de Términos y Privacidad (feature 028). Los documentos se leen en una
 *  ventana encima de la pantalla, sin perder lo que se estaba llenando. */
export function AcceptTerms({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  const { m } = useI18n();
  const t = m.legal.accept;
  const [open, setOpen] = useState<LegalKind | null>(null);
  const link = (kind: LegalKind, label: string) => (
    <button type="button" className="underline" onClick={() => setOpen(kind)}>{label}</button>
  );
  return (
    <>
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
          {link("terms", t.terms)}
          {t.and}
          {link("privacy", t.privacy)}
          {t.after}
        </span>
      </label>
      {open && <LegalDialog kind={open} onClose={() => setOpen(null)} />}
    </>
  );
}
