"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { dateWithYear } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { HorizonStatus } from "@/lib/types";

/** Aviso "menos de 12 meses con precio" (feature 023): botón o enlace a "Extender precios". */
export function HorizonBanner({ status, onExtend }: { status?: HorizonStatus; onExtend?: () => void }) {
  const { m } = useI18n();
  const t = m.extension;
  if (!status) return null;
  const closed = status.closed_nights > 0 && status.first_closed_night;
  const short = status.needs_extension && status.first_unpriced_night;
  if (!closed && !short) return null;
  // Última noche CON precio = la víspera de la primera sin precio.
  let last = "";
  if (short) {
    const [y, mo, d] = status.first_unpriced_night!.split("-").map(Number);
    last = new Date(Date.UTC(y, mo - 1, d - 1)).toISOString().slice(0, 10);
  }
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
      <AlertTriangle size={18} className="shrink-0 text-amber-600" />
      <div className="min-w-0 flex-1 space-y-1">
        {closed && (
          <div>
            <p className="font-medium">{t.bannerClosedTitle}</p>
            <p className="text-muted-foreground">
              {t.bannerClosedText(status.closed_nights, dateWithYear(status.first_closed_night!))}
            </p>
          </div>
        )}
        {short && (
          <div>
            <p className="font-medium">{t.bannerTitle}</p>
            <p className="text-muted-foreground">{t.bannerText(dateWithYear(last), status.months_covered)}</p>
          </div>
        )}
      </div>
      {onExtend ? (
        <Button className="h-8 px-3 text-xs" onClick={onExtend}>
          {t.extendCta}
        </Button>
      ) : (
        <Link
          href="/calendar?extend=1"
          className="inline-flex h-8 items-center rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:opacity-90"
        >
          {t.extendCta}
        </Link>
      )}
    </div>
  );
}
