"use client";

import { useQuery } from "@tanstack/react-query";
import { PriceCalendar } from "@/components/calendar/price-calendar";
import { Kpi } from "@/components/dashboard/kpi";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useActiveUnit } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { formatCOP, monthLabel, monthRange } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

export default function DashboardPage() {
  const { m } = useI18n();
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
  const status = useQuery({
    queryKey: ["system-status"],
    queryFn: () => api.getStatus(),
    staleTime: 60_000,
  });
  const kpis = useQuery({
    queryKey: ["month-kpis", unitTypeId, from, to],
    queryFn: () => api.getKpis(unitTypeId, from, to),
    staleTime: 60_000,
  });
  const deals = useQuery({
    queryKey: ["native-deals"],
    queryFn: () => api.listNativeDeals(),
    staleTime: 60_000,
  });

  const CHANNEL_NAMES: Record<string, string> = {
    booking: "Booking.com",
    airbnb: "Airbnb",
    direct: m.dashboard.direct,
  };
  const channels = status.data?.channels ?? [];

  const days = calendar.data ?? [];
  // Solo días con datos (precio): evita contar días pasados/sin importar como ocupados.
  const withData = days.filter((d) => d.base_price !== null);
  const occupied = withData.filter((d) => d.available === 0).length;
  const occupancy = withData.length ? Math.round((occupied / withData.length) * 100) : 0;
  const promos = days.filter((d) => d.promotions.length > 0).length;

  // Días del mes con deal nativo activo (extremos abiertos = cubren siempre por ese lado).
  const activeDeals = (deals.data?.deals ?? []).filter((d) => d.is_active);
  const nativeDealDates = new Set<string>();
  for (const d of days) {
    if (
      activeDeals.some(
        (deal) =>
          (!deal.date_from || deal.date_from <= d.date) &&
          (!deal.date_to || deal.date_to >= d.date),
      )
    ) {
      nativeDealDates.add(d.date);
    }
  }

  const reserved = kpis.data?.reserved_nights;
  const reservedHint = reserved
    ? [
        `Booking ${reserved.booking}`,
        `Airbnb ${reserved.airbnb}`,
        ...(reserved.direct > 0 ? [`${m.dashboard.direct} ${reserved.direct}`] : []),
      ].join(" · ")
    : undefined;

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <h1 className="text-xl font-semibold">{m.dashboard.title}</h1>

      {calendar.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          <Kpi
            label={m.dashboard.occupancy}
            value={`${occupancy}%`}
            hint={m.dashboard.occupiedNights(occupied)}
          />
          <Kpi
            label={m.dashboard.reservedNights}
            value={String(kpis.data?.total_reserved ?? "—")}
            hint={reservedHint}
          />
          <Kpi
            label={m.dashboard.blockedNights}
            value={String(kpis.data?.blocked_nights ?? "—")}
            hint={m.dashboard.blockedHint}
          />
          <Kpi label={m.dashboard.pendingSuggestions} value={String(suggestions.data?.length ?? 0)} />
          <Kpi label={m.dashboard.promoDays} value={String(promos)} />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
        <Card>
          <p className="mb-2 text-sm font-medium">
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
              nativeDealDates={nativeDealDates}
            />
          )}
        </Card>

        <div className="space-y-4">
        <Card>
          <p className="mb-2 text-sm font-medium">{m.dashboard.channels}</p>
          {status.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : !channels.length ? (
            <p className="text-xs text-muted-foreground">
              {m.dashboard.noChannelData}
            </p>
          ) : (
            <ul className="space-y-2 text-xs">
              {channels.map((c) => (
                <li
                  key={c.kind}
                  className="flex items-center justify-between rounded-md border border-border px-2 py-1"
                >
                  <span className="flex items-center gap-2">
                    <span
                      className={`inline-block h-2 w-2 rounded-full ${
                        c.is_active ? "bg-emerald-500" : "bg-muted-foreground/40"
                      }`}
                      title={c.is_active ? m.dashboard.connected : m.dashboard.inactive}
                    />
                    {CHANNEL_NAMES[c.kind] ?? c.kind}
                  </span>
                  <span className="text-muted-foreground">
                    {m.dashboard.bookings(c.bookings)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <p className="mb-2 text-sm font-medium">{m.dashboard.recentSuggestions}</p>
          {suggestions.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !suggestions.data?.length ? (
            <p className="text-xs text-muted-foreground">{m.dashboard.noPendingSuggestions}</p>
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
    </div>
  );
}
