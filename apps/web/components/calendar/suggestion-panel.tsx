"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Rationale } from "@/components/suggestions/rationale";
import { api } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Suggestion } from "@/lib/types";

interface Props {
  date: string;
  suggestions: Suggestion[];
}

/** Detalle y resolución de las sugerencias vigentes del día seleccionado (feature 014).
 *  El detalle mostrado es la previsualización informada; el clic es la confirmación. */
export function SuggestionPanel({ date, suggestions }: Props) {
  const { m } = useI18n();
  const qc = useQueryClient();
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["suggestions"] });
    qc.invalidateQueries({ queryKey: ["calendar"] });
  };

  const apply = useMutation({
    mutationFn: (id: number) => api.applySuggestion(id),
    onSuccess: (s) => {
      if (s.applied_from && s.applied_from > s.date_from) {
        toast.success(m.calendar.appliedFrom(s.applied_from));
      } else {
        toast.success(m.calendar.appliedPublished);
      }
    },
    onError: (e: Error) => toast.error(e.message),
    onSettled: refresh,
  });
  const reject = useMutation({
    mutationFn: (id: number) => api.rejectSuggestion(id),
    onSuccess: () => toast(m.calendar.rejected),
    onError: (e: Error) => toast.error(e.message),
    onSettled: refresh,
  });
  const busy = apply.isPending || reject.isPending;

  return (
    <Card>
      <p className="mb-2 text-xs font-medium">
        {m.calendar.suggestionsHeader(suggestions.length)} · {date}
      </p>
      <div className="space-y-3">
        {suggestions.map((s) => (
          <div key={s.id} className="space-y-1 rounded-md border border-border p-2">
            <div className="flex items-center justify-between text-xs">
              <span>
                {s.current_price ? (
                  <>
                    <span className="text-muted-foreground">{formatCOP(s.current_price)} → </span>
                    <strong>{formatCOP(s.suggested_price)}</strong>
                  </>
                ) : (
                  <strong>{formatCOP(s.suggested_price)}</strong>
                )}
              </span>
              {s.confidence && (
                <Badge variant="muted">{Math.round(Number(s.confidence) * 100)}%</Badge>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground">
              {s.date_from === s.date_to ? s.date_from : `${s.date_from} → ${s.date_to}`}
            </p>
            <Rationale rationale={s.rationale} />
            <div className="flex gap-2 pt-1">
              <Button onClick={() => apply.mutate(s.id)} disabled={busy}>
                {m.calendar.approveApply}
              </Button>
              <Button
                className="bg-muted text-foreground"
                onClick={() => reject.mutate(s.id)}
                disabled={busy}
              >
                {m.calendar.reject}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
