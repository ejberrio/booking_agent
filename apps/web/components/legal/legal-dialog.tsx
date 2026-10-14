"use client";

import { X } from "lucide-react";
import { useEffect } from "react";
import { LegalDoc, type LegalKind } from "@/components/legal/legal-doc";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";

/** Lee los Términos o la Privacidad encima de la pantalla actual, sin salir de ella (así no
 *  se pierde el formulario ni la pantalla de aceptación, también dentro de la app). */
export function LegalDialog({ kind, onClose }: { kind: LegalKind; onClose: () => void }) {
  const { m } = useI18n();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/60 p-4"
      role="dialog" aria-modal="true" onClick={onClose}>
      <div className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-xl border border-border bg-card"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-end p-2">
          <button type="button" onClick={onClose} aria-label={m.legal.accept.close}
            className="rounded-md p-1 text-muted-foreground hover:bg-muted">
            <X size={18} />
          </button>
        </div>
        <div className="overflow-y-auto px-5 pb-4">
          <LegalDoc kind={kind} />
        </div>
        <div className="border-t border-border p-3 text-right">
          <Button onClick={onClose}>{m.legal.accept.close}</Button>
        </div>
      </div>
    </div>
  );
}
