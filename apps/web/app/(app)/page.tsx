"use client";

import { useQuery } from "@tanstack/react-query";
import { PriceCalendar } from "@/components/calendar/price-calendar";
import { Kpi } from "@/components/dashboard/kpi";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useActiveUnit } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { formatCOP, monthLabel, monthRange } from "@/lib/format";

export default function DashboardPage() {
  const [unitTypeId] = useActiveUnit();
  const now = new Date();
  const { from, to } = monthRange(now.getFullYear(), now.getMonth());

  const calendar = useQuery({
    queryKey: ["calendar", unitTypeId, from, to],
    queryFn: () => api.getCalendar(unitTypeId, from, to),
  });
  const suggestions = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api.listSuggestions("proposed"),
  });

  const days = calendar.data ?? [];
  // Solo días con datos (precio): evita contar días pasados/sin importar como ocupados.
  const withData = days.filter((d) => d.base_price !== null);
  const occupied = withData.filter((d) => d.available === 0).length;
  const occupancy = withData.length ? Math.round((occupied / withData.length) * 100) : 0;
  const promos = days.filter((d) => d.promotions.length > 0).length;

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <h1 className="text-xl font-semibold">Panorama</h1>

      {calendar.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Kpi label="Ocupación (mes)" value={`${occupancy}%`} hint={`${occupied} noches reservadas`} />
          <Kpi label="Sugerencias pendientes" value={String(suggestions.data?.length ?? 0)} />
          <Kpi label="Días con promoción" value={String(promos)} />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
        <Card>
          <p className="mb-2 text-sm font-medium capitalize">
            {monthLabel(now.getFullYear(), now.getMonth())}
          </p>
          {calendar.isLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <PriceCalendar
              year={now.getFullYear()}
              month={now.getMonth()}
              days={days}
              selection={null}
              onSelect={() => {}}
            />
          )}
        </Card>

        <Card>
          <p className="mb-2 text-sm font-medium">Sugerencias recientes</p>
          {suggestions.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !suggestions.data?.length ? (
            <p className="text-xs text-muted-foreground">Sin sugerencias pendientes.</p>
          ) : (
            <ul className="space-y-2 text-xs">
              {suggestions.data.slice(0, 5).map((s) => (
                <li key={s.id} className="rounded-md border border-border px-2 py-1">
                  <span className="font-medium">{formatCOP(s.suggested_price)}</span> · {s.date_from}
                  {s.rationale?.text ? ` — ${s.rationale.text}` : ""}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
