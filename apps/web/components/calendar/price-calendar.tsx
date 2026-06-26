"use client";

import { useMemo, useState } from "react";
import type { CalendarDay } from "@/lib/types";
import { ymd } from "@/lib/format";
import { cn } from "@/lib/utils";

const WEEKDAYS = ["L", "M", "X", "J", "V", "S", "D"];

interface Props {
  year: number;
  month: number; // 0-11
  days: CalendarDay[];
  selection: { from: string; to: string } | null;
  onSelect: (from: string, to: string) => void;
}

export function PriceCalendar({ year, month, days, selection, onSelect }: Props) {
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
        {WEEKDAYS.map((w) => (
          <div key={w}>{w}</div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((date, i) => {
          if (!date) return <div key={i} />;
          const d = byDate.get(date);
          const eff = d?.effective_price ? Number(d.effective_price) : null;
          const ratio = eff !== null && max > min ? (eff - min) / (max - min) : 0;
          const selected = inRange(date);
          return (
            <button
              key={date}
              onPointerDown={() => {
                setDragStart(date);
                setDragEnd(date);
              }}
              onPointerEnter={() => dragStart && setDragEnd(date)}
              style={eff !== null ? { backgroundColor: `rgba(37,99,235,${0.12 + ratio * 0.5})` } : undefined}
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
                {d?.promotions.length ? <span className="h-1 w-1 rounded-full bg-amber-500" /> : null}
                {d && d.available === 0 ? <span className="h-1 w-1 rounded-full bg-red-500" /> : null}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
