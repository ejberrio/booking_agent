"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatCOP } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Messages } from "@/lib/i18n/messages";
import type { NativeDeal, Promotion } from "@/lib/types";

const CHANNEL_NAMES: Record<string, string> = { booking: "Booking.com", airbnb: "Airbnb" };

function scopeLabel(scope: string[] | null, m: Messages): string {
  if (!scope) return m.calendar.allChannels;
  return scope.map((c) => CHANNEL_NAMES[c] ?? c).join(" + ");
}

function dealVigencia(d: NativeDeal, m: Messages): string {
  if (!d.date_from && !d.date_to) return m.calendar.alwaysActive;
  if (d.date_from && d.date_to) return `${d.date_from} → ${d.date_to}`;
  return d.date_from ? m.calendar.since(d.date_from) : m.calendar.until(d.date_to ?? "");
}

function pct(value: string | null): string {
  if (value === null) return "";
  return `${Number(value) % 1 === 0 ? Number(value) : value}%`;
}

interface Props {
  date: string;
  promotions: Promotion[];
  deals: NativeDeal[];
}

/** Detalle informativo de las ofertas que aplican al día seleccionado (feature 015).
 *  Sin acciones: las promos se gestionan en Ofertas; los deals, en el panel del canal. */
export function OffersPanel({ date, promotions, deals }: Props) {
  const { m } = useI18n();
  if (!promotions.length && !deals.length) return null;
  return (
    <Card>
      <p className="mb-2 text-xs font-medium">{m.calendar.dayOffers} · {date}</p>
      <div className="space-y-2">
        {promotions.map((p) => (
          <div key={`p-${p.id}`} className="space-y-0.5 rounded-md border border-border p-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-medium">{p.name}</span>
              <Badge variant="muted">{m.calendar.appPromo}</Badge>
            </div>
            <p className="text-muted-foreground">
              {p.discount_pct ? `${pct(p.discount_pct)} · ` : ""}
              {formatCOP(p.price)} · {scopeLabel(p.channels_scope, m)}
            </p>
            <p className="text-[10px] text-muted-foreground">
              {p.first_night} → {p.last_night}
            </p>
          </div>
        ))}
        {deals.map((d) => (
          <div key={`d-${d.id}`} className="space-y-0.5 rounded-md border border-border p-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-medium">{d.name}</span>
              <Badge variant="muted">{m.calendar.nativeDeal}</Badge>
            </div>
            <p className="text-muted-foreground">
              {pct(d.discount_pct)} · {CHANNEL_NAMES[d.channel] ?? d.channel}
            </p>
            <p className="text-[10px] text-muted-foreground">{dealVigencia(d, m)}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
