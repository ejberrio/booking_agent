"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Rationale } from "@/components/suggestions/rationale";
import { formatCOP, pctChange, shortDate, shortRange } from "@/lib/format";
import type { SuggestionBlock as Block } from "@/lib/types";

interface Props {
  block: Block;
  selected: Set<number>;
  onToggle: (ids: number[], checked: boolean) => void;
  onApplyOne: (id: number) => void;
  onRejectOne: (id: number) => void;
  busy?: boolean;
}

const DIRECTION = {
  up: { label: "sube", variant: "success" },
  down: { label: "baja", variant: "warning" },
  mixed: { label: "sube y baja", variant: "muted" },
} as const;

/** Casilla con estado "parcial" (algunas sugerencias del bloque marcadas). */
function Check({
  checked,
  partial,
  onChange,
  label,
}: {
  checked: boolean;
  partial?: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = !!partial && !checked;
  }, [partial, checked]);
  return (
    <input
      ref={ref}
      type="checkbox"
      aria-label={label}
      className="h-4 w-4 shrink-0 accent-[var(--primary)]"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
    />
  );
}

/** Bloque por evento o periodo (feature 019): se marca entero o por sugerencia. */
export function SuggestionBlock({ block, selected, onToggle, onApplyOne, onRejectOne, busy }: Props) {
  const [open, setOpen] = useState(false);
  const marked = block.suggestion_ids.filter((id) => selected.has(id)).length;
  const all = marked === block.suggestion_ids.length;
  const dir = DIRECTION[block.direction];
  const nights = block.nights.length;

  return (
    <Card className="space-y-2">
      <div className="flex items-start gap-3">
        <Check
          checked={all}
          partial={marked > 0}
          onChange={(v) => onToggle(block.suggestion_ids, v)}
          label={`Seleccionar ${block.title}`}
        />
        <button
          type="button"
          className="flex min-w-0 flex-1 items-start justify-between gap-2 text-left"
          onClick={() => setOpen((o) => !o)}
        >
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium">
              {block.title} · {shortRange(block.date_from, block.date_to)}
            </span>
            <span className="block text-xs text-muted-foreground">
              {nights} noche{nights !== 1 ? "s" : ""} ·{" "}
              {block.nights
                .slice(0, 3)
                .map((n) => `${shortDate(n.date)} ${formatCOP(n.suggested_price)}`)
                .join(" · ")}
              {nights > 3 ? " …" : ""}
            </span>
          </span>
          <span className="flex shrink-0 items-center gap-1">
            <Badge variant={dir.variant}>{dir.label}</Badge>
            {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </span>
        </button>
      </div>

      {open && (
        <div className="space-y-3 border-t border-border pt-2">
          {block.suggestions.map((s) => {
            const mine = block.nights.filter((n) => n.suggestion_id === s.id);
            const first = mine[0];
            return (
              <div key={s.id} className="space-y-1.5">
                <div className="flex items-start gap-3">
                  <Check
                    checked={selected.has(s.id)}
                    onChange={(v) => onToggle([s.id], v)}
                    label={`Seleccionar sugerencia ${shortRange(s.date_from, s.date_to)}`}
                  />
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="text-sm">
                      <span className="font-medium">{shortRange(s.date_from, s.date_to)}</span>{" "}
                      <span className="text-muted-foreground">
                        {formatCOP(first?.current_price)} →{" "}
                      </span>
                      <span className="font-medium">{formatCOP(s.suggested_price)}</span>{" "}
                      <span className="text-xs text-muted-foreground">
                        {pctChange(first?.current_price ?? null, s.suggested_price)}
                      </span>
                    </p>
                    {s.occupied_count > 0 && (
                      <p className="text-[11px] text-amber-600">
                        {s.sellable_count} de {s.total_nights} noches · {s.occupied_count} ya
                        reservada{s.occupied_count !== 1 ? "s" : ""} o bloqueada
                        {s.occupied_count !== 1 ? "s" : ""}
                      </p>
                    )}
                    <Rationale rationale={s.rationale} />
                    <div className="flex gap-2 pt-0.5">
                      <Button
                        className="h-7 px-2 text-xs"
                        onClick={() => onApplyOne(s.id)}
                        disabled={busy}
                      >
                        Aplicar solo esta
                      </Button>
                      <Button
                        className="h-7 bg-muted px-2 text-xs text-foreground"
                        onClick={() => onRejectOne(s.id)}
                        disabled={busy}
                      >
                        Rechazar
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
