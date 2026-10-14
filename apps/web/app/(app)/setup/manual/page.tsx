"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

// Modo sin conexión (feature 029): el anfitrión crea su apartamento a mano.
export default function ManualSetupPage() {
  const { m } = useI18n();
  const t = m.offline.setup;
  const router = useRouter();
  const qc = useQueryClient();
  const [f, setF] = useState({
    name: "", city: "", currency: "COP", weekday: "", weekend: "",
    airbnb_url: "", airbnb_ical: "", booking_url: "", booking_ical: "",
  });
  const [busy, setBusy] = useState(false);
  // Feature 030: si la cuenta viene del informe gratis, se prellenan municipio y precios.
  const report = useQuery({ queryKey: ["my-report"], queryFn: api.myReport, retry: false });
  const [prefilled, setPrefilled] = useState(false);
  useEffect(() => {
    const r = report.data;
    if (!r || prefilled) return;
    setPrefilled(true);
    const digits = (v: string | null) => (v ? String(Math.round(Number(v))) : "");
    setF((cur) => ({
      ...cur,
      city: cur.city || r.city,
      currency: r.currency || cur.currency,
      weekday: cur.weekday || digits(r.weekday_price),
      weekend: cur.weekend || digits(r.weekend_price),
    }));
  }, [report.data, prefilled]);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setF({ ...f, [k]: e.target.value });
  const num = (v: string) => Number(v.replace(/[^\d]/g, ""));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.createManualApartment({
        name: f.name, city: f.city, currency: f.currency.toUpperCase(),
        weekday_price: num(f.weekday),
        weekend_price: f.weekend ? num(f.weekend) : undefined,
        airbnb_url: f.airbnb_url || undefined, airbnb_ical: f.airbnb_ical || undefined,
        booking_url: f.booking_url || undefined, booking_ical: f.booking_ical || undefined,
      });
      toast.success(t.created);
      await qc.invalidateQueries();
      router.push("/");
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <Card className="space-y-3">
        <CardTitle>{t.title}</CardTitle>
        <CardDescription>{t.description}</CardDescription>
        {prefilled && (
          <p className="text-xs text-muted-foreground">
            {m.pub.app.prefilled}{" "}
            <Link href="/report" className="underline">{m.pub.app.seeReport}</Link>
          </p>
        )}
        <form onSubmit={submit} className="space-y-3">
          <Input placeholder={t.name} value={f.name} onChange={set("name")} required maxLength={200} />
          <div className="flex gap-2">
            <Input placeholder={t.city} value={f.city} onChange={set("city")} required maxLength={120} />
            <Input className="w-24" aria-label={t.currency} title={t.currency} value={f.currency}
              onChange={set("currency")} maxLength={3} required />
          </div>
          <Input inputMode="numeric" placeholder={t.weekday} value={f.weekday}
            onChange={set("weekday")} required />
          <Input inputMode="numeric" placeholder={t.weekend} value={f.weekend} onChange={set("weekend")} />
          <div className="space-y-2 border-t pt-3">
            <p className="text-sm font-medium">{t.listings}</p>
            <p className="text-xs text-muted-foreground">{t.listingsHint}</p>
            <Input type="text" inputMode="url" autoCapitalize="none" placeholder={t.airbnbUrl} value={f.airbnb_url} onChange={set("airbnb_url")} />
            <Input type="text" inputMode="url" autoCapitalize="none" placeholder={t.airbnbIcal} value={f.airbnb_ical} onChange={set("airbnb_ical")} />
            <Input type="text" inputMode="url" autoCapitalize="none" placeholder={t.bookingUrl} value={f.booking_url} onChange={set("booking_url")} />
            <Input type="text" inputMode="url" autoCapitalize="none" placeholder={t.bookingIcal} value={f.booking_ical} onChange={set("booking_ical")} />
            <p className="text-xs text-muted-foreground">{t.icalHelp}</p>
          </div>
          <Button type="submit" className="w-full" disabled={busy || !f.name || !f.city || !num(f.weekday)}>
            {busy ? t.creating : t.submit}
          </Button>
        </form>
      </Card>
    </div>
  );
}
