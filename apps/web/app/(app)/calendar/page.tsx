"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarPlus, ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useEffect, useState } from "react";
import { PriceCalendar } from "@/components/calendar/price-calendar";
import { RangeEditor } from "@/components/calendar/range-editor";
import { DayInfoPanel } from "@/components/calendar/day-info-panel";
import { ExtendPricesDialog } from "@/components/calendar/extend-prices-dialog";
import { HorizonBanner } from "@/components/calendar/horizon-banner";
import { OffersPanel } from "@/components/calendar/offers-panel";
import { SuggestionPanel } from "@/components/calendar/suggestion-panel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useActiveUnit } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { formatNumber, monthLabel, monthRange, ymd } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { NativeDeal, Suggestion } from "@/lib/types";

function dealCoversDay(deal: NativeDeal, day: string): boolean {
  // Extremos abiertos: sin fecha = cubre por ese lado.
  return (!deal.date_from || deal.date_from <= day) && (!deal.date_to || deal.date_to >= day);
}

export default function CalendarPage() {
  const { m } = useI18n();
  const [unitTypeId] = useActiveUnit();
  const qc = useQueryClient();
  const now = new Date();
  const [ym, setYm] = useState({ year: now.getFullYear(), month: now.getMonth() });
  const [selection, setSelection] = useState<{ from: string; to: string } | null>(null);
  const { from, to } = monthRange(ym.year, ym.month);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["calendar", unitTypeId, from, to],
    queryFn: () => api.getCalendar(unitTypeId, from, to),
  });
  const offsets = useQuery({
    queryKey: ["channel-offsets"],
    queryFn: () => api.getChannelOffsets(),
    staleTime: 5 * 60_000,
  });
  const suggestions = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api.listSuggestions("proposed"),
  });
  const deals = useQuery({
    queryKey: ["native-deals"],
    queryFn: () => api.listNativeDeals(),
    staleTime: 60_000,
  });
  const promotions = useQuery({
    queryKey: ["promotions", unitTypeId],
    queryFn: () => api.listPromotions(unitTypeId),
    staleTime: 60_000,
  });
  const bookings = useQuery({
    queryKey: ["bookings", unitTypeId, from, to],
    queryFn: () => api.listBookings(unitTypeId, from, to),
    staleTime: 60_000,
  });
  const notes = useQuery({
    queryKey: ["calendar-notes", unitTypeId],
    queryFn: () => api.listCalendarNotes(unitTypeId),
  });
  // Horizonte de precios + diálogo "Extender precios" (feature 023). `?extend=1` lo abre.
  const horizon = useQuery({
    queryKey: ["horizon-status", unitTypeId],
    queryFn: () => api.getHorizonStatus(unitTypeId),
    staleTime: 5 * 60_000,
  });
  const [extendOpen, setExtendOpen] = useState(false);
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("extend") === "1") setExtendOpen(true);
  }, []);

  // Sugerencias vigentes (proposed y con al menos un día no pasado) por fecha.
  const today = ymd(new Date());
  const suggestionsByDate = new Map<string, Suggestion[]>();
  for (const s of suggestions.data ?? []) {
    if (s.date_to < today) continue; // vencida: no genera marcador
    for (let d = new Date(`${s.date_from}T00:00:00Z`); ; d.setUTCDate(d.getUTCDate() + 1)) {
      const key = ymd(d);
      if (key > s.date_to) break;
      if (key >= today) suggestionsByDate.set(key, [...(suggestionsByDate.get(key) ?? []), s]);
    }
  }
  const suggestionDates = new Set(suggestionsByDate.keys());

  // Días del mes visible cubiertos por deals nativos ACTIVOS (extremos abiertos).
  const activeDeals = (deals.data?.deals ?? []).filter((d) => d.is_active);
  const nativeDealDates = new Set<string>();
  if (activeDeals.length) {
    const { from: mFrom, to: mTo } = monthRange(ym.year, ym.month);
    for (let d = new Date(`${mFrom}T00:00:00Z`); ; d.setUTCDate(d.getUTCDate() + 1)) {
      const key = ymd(d);
      if (key > mTo) break;
      if (activeDeals.some((deal) => dealCoversDay(deal, key))) nativeDealDates.add(key);
    }
  }
  const dealsOfDay = (day: string) => activeDeals.filter((d) => dealCoversDay(d, day));
  const promosOfDay = (day: string) =>
    (promotions.data?.promotions ?? []).filter(
      (p) => p.status !== "retired" && p.first_night <= day && p.last_night >= day,
    );

  // Reservas cuya NOCHE es el día (el día de salida no ocupa) y notas del rango.
  const bookingsOfNight = (day: string) =>
    (bookings.data?.bookings ?? []).filter((b) => b.check_in <= day && day < b.check_out);
  const allNotes = notes.data?.notes ?? [];
  const notesCovering = (fromD: string, toD: string) =>
    allNotes.filter((n) => n.date_from <= toD && n.date_to >= fromD);
  // Sincronización manual con el Channel Manager (cancelaciones, reservas nuevas…).
  const syncNow = useMutation({
    mutationFn: () => api.importRemote(365),
    onSuccess: (r) => {
      toast.success(m.calendar.synced(r.created, r.updated, r.issues));
      qc.invalidateQueries();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // Noches reservadas del mes visible (el día de salida no ocupa).
  const bookedDates = new Set<string>();
  for (const b of bookings.data?.bookings ?? []) {
    for (let d = new Date(`${b.check_in}T00:00:00Z`); ; d.setUTCDate(d.getUTCDate() + 1)) {
      const key = ymd(d);
      if (key >= b.check_out) break;
      bookedDates.add(key);
    }
  }

  const noteDates = new Set<string>();
  if (allNotes.length) {
    const { from: mFrom, to: mTo } = monthRange(ym.year, ym.month);
    for (let d = new Date(`${mFrom}T00:00:00Z`); ; d.setUTCDate(d.getUTCDate() + 1)) {
      const key = ymd(d);
      if (key > mTo) break;
      if (allNotes.some((n) => n.date_from <= key && n.date_to >= key)) noteDates.add(key);
    }
  }

  // Precio efectivo por canal del día seleccionado (solo si hay offsets ≠ 0;
  // con 0/null el panel queda exactamente igual que antes).
  const CHANNEL_NAMES: Record<string, string> = { booking: "Booking.com", airbnb: "Airbnb" };
  const activeOffsets = (offsets.data?.offsets ?? []).filter((o) => o.offset_pct);
  const selectedDay = selection
    ? (data ?? []).find((d) => d.date === selection.from)
    : undefined;
  const channelPrices =
    activeOffsets.length && selectedDay?.base_price
      ? [
          { name: "Booking.com", value: Number(selectedDay.base_price), note: "" },
          ...activeOffsets.map((o) => ({
            name: CHANNEL_NAMES[o.channel] ?? o.channel,
            value: Math.round(Number(selectedDay.base_price) * (1 + (o.offset_pct ?? 0) / 100)),
            note: ` (${(o.offset_pct ?? 0) > 0 ? "+" : ""}${o.offset_pct}%)`,
          })),
        ]
      : null;

  function move(delta: number) {
    setSelection(null);
    setYm((s) => {
      const d = new Date(s.year, s.month + delta, 1);
      return { year: d.getFullYear(), month: d.getMonth() };
    });
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-semibold">{m.calendar.title}</h1>
        <div className="flex items-center gap-2">
          <Button
            className="bg-muted text-foreground"
            onClick={() => setExtendOpen(true)}
            title={m.extension.title}
          >
            <CalendarPlus size={16} />
            <span className="ml-1 hidden lg:inline">{m.extension.extendCta}</span>
          </Button>
          <Button
            className="bg-muted text-foreground"
            onClick={() => syncNow.mutate()}
            disabled={syncNow.isPending}
            title={m.calendar.syncTitle}
          >
            <RefreshCw size={16} className={syncNow.isPending ? "animate-spin" : ""} />
            <span className="ml-1 hidden sm:inline">{m.calendar.sync}</span>
          </Button>
          <Button className="bg-muted text-foreground" onClick={() => move(-1)}>
            <ChevronLeft size={16} />
          </Button>
          <span className="w-36 text-center text-sm">
            {monthLabel(ym.year, ym.month)}
          </span>
          <Button className="bg-muted text-foreground" onClick={() => move(1)}>
            <ChevronRight size={16} />
          </Button>
        </div>
      </div>

      <HorizonBanner status={horizon.data} onExtend={() => setExtendOpen(true)} />
      {extendOpen && horizon.data && (
        <ExtendPricesDialog
          open
          unitTypeId={unitTypeId}
          defaultUntil={horizon.data.default_until}
          maxUntil={horizon.data.max_until}
          onClose={() => setExtendOpen(false)}
        />
      )}

      {isError ? (
        <Card>
          <p className="text-sm text-red-500">{m.calendar.loadError}</p>
          <Button className="mt-2" onClick={() => refetch()}>
            {m.common.retry}
          </Button>
        </Card>
      ) : isLoading ? (
        <Skeleton className="h-80 w-full" />
      ) : (
        <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
          <Card>
            <PriceCalendar
              year={ym.year}
              month={ym.month}
              days={data ?? []}
              selection={selection}
              onSelect={(f, t) => setSelection({ from: f, to: t })}
              suggestionDates={suggestionDates}
              nativeDealDates={nativeDealDates}
              noteDates={noteDates}
              bookedDates={bookedDates}
            />
          </Card>
          <div className="space-y-4">
            {selection &&
              selection.from === selection.to &&
              suggestionsByDate.has(selection.from) && (
                <SuggestionPanel
                  date={selection.from}
                  suggestions={suggestionsByDate.get(selection.from) ?? []}
                />
              )}
            {selection && selection.from === selection.to && (
              <OffersPanel
                date={selection.from}
                promotions={promosOfDay(selection.from)}
                deals={dealsOfDay(selection.from)}
              />
            )}
            {selection && (
              <DayInfoPanel
                unitTypeId={unitTypeId}
                selection={selection}
                bookings={
                  selection.from === selection.to ? bookingsOfNight(selection.from) : []
                }
                notes={notesCovering(selection.from, selection.to)}
              />
            )}
            <RangeEditor unitTypeId={unitTypeId} selection={selection} onApplied={() => refetch()} />
            {channelPrices && (
              <Card>
                <p className="text-xs font-medium">{m.calendar.channelPrice} · {selection?.from}</p>
                <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                  {channelPrices.map((c) => (
                    <li key={c.name}>
                      {c.name}: <strong className="text-foreground">{formatNumber(c.value)} COP</strong>
                      {c.note && <span>{c.note}</span>}
                    </li>
                  ))}
                </ul>
                <p className="mt-1 text-[10px] text-muted-foreground">
                  {m.calendar.airbnbCurrencyNote}
                </p>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
