"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { PriceCalendar } from "@/components/calendar/price-calendar";
import { RangeEditor } from "@/components/calendar/range-editor";
import { OffersPanel } from "@/components/calendar/offers-panel";
import { SuggestionPanel } from "@/components/calendar/suggestion-panel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useActiveUnit } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { monthLabel, monthRange, ymd } from "@/lib/format";
import type { NativeDeal, Suggestion } from "@/lib/types";

function dealCoversDay(deal: NativeDeal, day: string): boolean {
  // Extremos abiertos: sin fecha = cubre por ese lado.
  return (!deal.date_from || deal.date_from <= day) && (!deal.date_to || deal.date_to >= day);
}

export default function CalendarPage() {
  const [unitTypeId] = useActiveUnit();
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
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Calendario de precios</h1>
        <div className="flex items-center gap-2">
          <Button className="bg-muted text-foreground" onClick={() => move(-1)}>
            <ChevronLeft size={16} />
          </Button>
          <span className="w-36 text-center text-sm capitalize">
            {monthLabel(ym.year, ym.month)}
          </span>
          <Button className="bg-muted text-foreground" onClick={() => move(1)}>
            <ChevronRight size={16} />
          </Button>
        </div>
      </div>

      {isError ? (
        <Card>
          <p className="text-sm text-red-500">No se pudo cargar el calendario.</p>
          <Button className="mt-2" onClick={() => refetch()}>
            Reintentar
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
            <RangeEditor unitTypeId={unitTypeId} selection={selection} onApplied={() => refetch()} />
            {channelPrices && (
              <Card>
                <p className="text-xs font-medium">Precio por canal · {selection?.from}</p>
                <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                  {channelPrices.map((c) => (
                    <li key={c.name}>
                      {c.name}: <strong className="text-foreground">{c.value.toLocaleString("es-CO")} COP</strong>
                      {c.note && <span>{c.note}</span>}
                    </li>
                  ))}
                </ul>
                <p className="mt-1 text-[10px] text-muted-foreground">
                  Airbnb lo muestra en la moneda del huésped (margen cambiario propio).
                </p>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
