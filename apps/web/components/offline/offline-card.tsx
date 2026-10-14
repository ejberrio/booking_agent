"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { IcalReport, ManualApartment } from "@/lib/types";

const NAMES: Record<string, string> = { airbnb: "Airbnb", booking: "Booking" };

/** Enlaces para aplicar precios a mano (feature 029). Se usa en Ajustes y en Sugerencias. */
export function ManualLinks({ apartment }: { apartment: ManualApartment }) {
  const { m } = useI18n();
  const t = m.offline.card;
  return (
    <div className="flex flex-wrap gap-2">
      {apartment.channels.filter((c) => c.calendar_url).map((c) => (
        <a key={c.channel} href={c.calendar_url!} target="_blank" rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-muted">
          <ExternalLink size={12} /> {t.openCalendar(NAMES[c.channel] ?? c.channel)}
        </a>
      ))}
    </div>
  );
}

function ListingsEditor({ apartment }: { apartment: ManualApartment }) {
  const { m } = useI18n();
  const t = m.offline;
  const qc = useQueryClient();
  const [f, setF] = useState({ airbnb_url: "", airbnb_ical: "", booking_url: "", booking_ical: "" });
  const save = useMutation({
    mutationFn: () => api.updateManualListings(apartment.property_id, {
      airbnb_url: f.airbnb_url || undefined, airbnb_ical: f.airbnb_ical || undefined,
      booking_url: f.booking_url || undefined, booking_ical: f.booking_ical || undefined,
    }),
    onSuccess: () => {
      toast.success(t.card.saved);
      qc.invalidateQueries({ queryKey: ["manual"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setF({ ...f, [k]: e.target.value });
  return (
    <div className="space-y-2">
      <Input type="text" inputMode="url" autoCapitalize="none" placeholder={t.setup.airbnbUrl} value={f.airbnb_url} onChange={set("airbnb_url")} />
      <Input type="text" inputMode="url" autoCapitalize="none" placeholder={t.setup.airbnbIcal} value={f.airbnb_ical} onChange={set("airbnb_ical")} />
      <Input type="text" inputMode="url" autoCapitalize="none" placeholder={t.setup.bookingUrl} value={f.booking_url} onChange={set("booking_url")} />
      <Input type="text" inputMode="url" autoCapitalize="none" placeholder={t.setup.bookingIcal} value={f.booking_ical} onChange={set("booking_ical")} />
      <p className="text-xs text-muted-foreground">{t.setup.icalHelp}</p>
      <Button onClick={() => save.mutate()} disabled={save.isPending}>{t.card.save}</Button>
    </div>
  );
}

/** Ajustes → Modo sin conexión (feature 029). */
export function OfflineCard() {
  const { m } = useI18n();
  const t = m.offline.card;
  const q = useQuery({ queryKey: ["manual"], queryFn: api.manualOverview });
  const [editing, setEditing] = useState<number | null>(null);
  const [report, setReport] = useState<IcalReport | null>(null);
  const sync = useMutation({
    mutationFn: api.syncIcal,
    onSuccess: (r) => setReport(r),
    onError: (e: Error) => toast.error(e.message),
  });
  if (q.data?.channel_mode !== "manual") return null;
  return (
    <Card className="space-y-3">
      <div className="flex items-center gap-2">
        <CardTitle>{t.title}</CardTitle>
        <Badge variant="warning">{m.offline.badge}</Badge>
      </div>
      <CardDescription>{t.description}</CardDescription>
      {q.data.apartments.map((a) => (
        <div key={a.property_id} className="space-y-2 rounded-lg border p-3">
          <p className="text-sm font-medium">{a.name} · {a.city} · {a.currency}</p>
          <ManualLinks apartment={a} />
          <ul className="text-xs text-muted-foreground">
            {a.channels.map((c) => (
              <li key={c.channel}>
                {NAMES[c.channel] ?? c.channel} · {t.ical}: {c.has_ical ? t.icalOn : t.icalOff}
                {c.listing_url && (
                  <a href={c.listing_url} target="_blank" rel="noreferrer" className="ml-2 underline">
                    {t.openListing}
                  </a>
                )}
              </li>
            ))}
          </ul>
          {editing === a.property_id ? (
            <ListingsEditor apartment={a} />
          ) : (
            <Button className="bg-muted text-foreground" onClick={() => setEditing(a.property_id)}>
              {t.edit}
            </Button>
          )}
        </div>
      ))}
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => sync.mutate()} disabled={sync.isPending}>
          {sync.isPending ? t.syncing : t.sync}
        </Button>
        {q.data.apartments.length < 5 && (
          <Link href="/setup/manual">
            <Button className="bg-muted text-foreground">{t.addAnother}</Button>
          </Link>
        )}
      </div>
      {report && (
        <p className="text-xs text-muted-foreground">
          {t.synced(report.bookings, report.cancelled)}
          {report.errors.length > 0 && ` ${t.syncErrors(report.errors.join("; "))}`}
        </p>
      )}
    </Card>
  );
}

/** Aviso en Sugerencias: en modo sin conexión los precios se copian a mano. */
export function OfflineBanner() {
  const { m } = useI18n();
  const q = useQuery({ queryKey: ["manual"], queryFn: api.manualOverview });
  if (q.data?.channel_mode !== "manual") return null;
  return (
    <div className="space-y-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
      <p>{m.offline.banner}</p>
      {q.data.apartments.map((a) => <ManualLinks key={a.property_id} apartment={a} />)}
    </div>
  );
}
