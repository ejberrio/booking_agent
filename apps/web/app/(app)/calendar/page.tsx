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
          <RangeEditor unitTypeId={unitTypeId} selection={selection} onApplied={() => refetch()} />
        </div>
      )}
    </div>
  );
}
