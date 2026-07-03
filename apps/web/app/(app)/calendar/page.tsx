"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { PriceCalendar } from "@/components/calendar/price-calendar";
import { RangeEditor } from "@/components/calendar/range-editor";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useActiveUnit } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { monthLabel, monthRange } from "@/lib/format";

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
            />
          </Card>
          <div className="space-y-4">
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
