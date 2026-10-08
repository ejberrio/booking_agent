"use client";

import { useMemo, useState } from "react";
import type { CalendarDay } from "@/lib/types";
import { weekdayShortNames, ymd } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

interface Props {
  year: number;
  month: number; // 0-11
  days: CalendarDay[];
  selection: { from: string; to: string } | null;
  onSelect: (from: string, to: string) => void;
  suggestionDates?: Set<string>;
  nativeDealDates?: Set<string>;
  noteDates?: Set<string>;
  /** Noches con reserva confirmada (de /bookings); prima sobre el inventario. */
  bookedDates?: Set<string>;
}

export function PriceCalendar({
  year,
  month,
  days,
  selection,
  onSelect,
  suggestionDates,
  nativeDealDates,
  noteDates,
  bookedDates,
}: Props) {
  const { m, lang } = useI18n();
  const weekdays = weekdayShortNames(lang);
  const byDate = useMemo(() => new Map(days.map((d) => [d.date, d])), [days]);
  const [dragStart, setDragStart] = useState<string | null>(null);
  const [dragEnd, setDragEnd] = useState<string | null>(null);

  const prices = days
    .map((d) => (d.effective_price ? Number(d.effective_price) : null))
    .filter((p): p is number => p !== null);
  const min = prices.length ? Math.min(...prices) : 0;
  const max = prices.length ? Math.max(...prices) : 1;

  const firstDow = (new Date(year, month, 1).getDay() + 6) % 7; // Lunes=0
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (string | null)[] = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => ymd(new Date(Date.UTC(year, month, i + 1)))),
  ];

  function inRange(date: string): boolean {
    const a = dragStart ?? selection?.from;
    const b = dragEnd ?? selection?.to;
    if (!a || !b) return false;
    const lo = a < b ? a : b;
    const hi = a < b ? b : a;
    return date >= lo && date <= hi;
  }

  function commit() {
    if (dragStart && dragEnd) {
      const lo = dragStart < dragEnd ? dragStart : dragEnd;
      const hi = dragStart < dragEnd ? dragEnd : dragStart;
      onSelect(lo, hi);
    }
    setDragStart(null);
    setDragEnd(null);
  }

  return (
    <div className="select-none" onPointerUp={commit} onPointerLeave={commit}>
      <div className="mb-1 grid grid-cols-7 gap-1 text-center text-[10px] text-muted-foreground">
        {weekdays.map((w, i) => (
          <div key={i} className="truncate">
            {w}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((date, i) => {
          if (!date) return <div key={i} />;
          const d = byDate.get(date);
          const eff = d?.effective_price ? Number(d.effective_price) : null;
          const ratio = eff !== null && max > min ? (eff - min) / (max - min) : 0;
          const selected = inRange(date);
          const blocked = d?.is_blocked === true;
          // Reservada si hay una reserva confirmada esa noche (fuente: reservas, también
          // para días pasados) o si el canal reporta 0 unidades sin bloqueo manual.
          const reserved =
            !blocked && (bookedDates?.has(date) === true || (!!d && d.available === 0));
          const bg = blocked
            ? "rgba(100,116,139,0.30)" // bloqueada: gris
            : reserved
              ? "rgba(239,68,68,0.18)" // reservada: rojo suave
              : eff !== null
              ? `rgba(37,99,235,${0.12 + ratio * 0.5})`
              : undefined;
          return (
            <button
              key={date}
              onPointerDown={() => {
                setDragStart(date);
                setDragEnd(date);
              }}
              onPointerEnter={() => dragStart && setDragEnd(date)}
              style={bg ? { backgroundColor: bg } : undefined}
              className={cn(
                "flex aspect-square flex-col items-center justify-center rounded-md border p-1 text-[10px]",
                selected ? "border-primary ring-1 ring-primary" : "border-border",
              )}
            >
              <span className="self-start font-medium">{Number(date.slice(8))}</span>
              <span className="font-semibold">
                {eff !== null ? `$${Math.round(eff / 1000)}k` : "—"}
              </span>
              <span className="flex gap-0.5">
                {suggestionDates?.has(date) ? (
                  <span title={m.calendar.legendSuggestion} className="h-1 w-1 rounded-full bg-violet-500" />
                ) : null}
                {d?.promotions.length ? (
                  <span title={m.calendar.legendPromotion} className="h-1 w-1 rounded-full bg-amber-500" />
                ) : null}
                {nativeDealDates?.has(date) ? (
                  <span title={m.calendar.legendNativeDeal} className="h-1 w-1 rounded-full bg-cyan-500" />
                ) : null}
                {noteDates?.has(date) ? (
                  <span title={m.calendar.legendNote} className="h-1 w-1 rounded-full bg-lime-500" />
                ) : null}
                {blocked ? (
                  <span title={m.calendar.legendBlocked} className="h-1 w-1 rounded-full bg-slate-400" />
                ) : null}
              </span>
              {reserved ? (
                <span title={m.calendar.legendBooked} className="mt-0.5 h-1 w-full rounded-full bg-red-500" />
              ) : null}
            </button>
          );
        })}
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-3 rounded-full bg-red-500" /> {m.calendar.legendBooked}
        </span>
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-slate-400" /> {m.calendar.legendBlocked}
        </span>
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> {m.calendar.legendPromotion}
        </span>
        {suggestionDates && suggestionDates.size > 0 ? (
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-violet-500" /> {m.calendar.legendSuggestion}
          </span>
        ) : null}
        {nativeDealDates && nativeDealDates.size > 0 ? (
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-500" /> {m.calendar.legendNativeDeal}
          </span>
        ) : null}
        {noteDates && noteDates.size > 0 ? (
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-lime-500" /> {m.calendar.legendNote}
          </span>
        ) : null}
        <span>{m.calendar.legendNoData}</span>
      </div>
    </div>
  );
}
