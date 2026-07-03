"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatCOP } from "@/lib/format";
import type { Suggestion } from "@/lib/types";

interface Props {
  suggestion: Suggestion;
  onReject: () => void;
  onApply: () => void;
  busy?: boolean;
}

const PENDING = new Set(["proposed", "approved"]);

export function SuggestionCard({ suggestion: s, onReject, onApply, busy }: Props) {
  const range = s.date_from === s.date_to ? s.date_from : `${s.date_from} → ${s.date_to}`;
  return (
    <Card className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          {s.current_price ? (
            <>
              <span className="font-normal text-muted-foreground">
                {formatCOP(s.current_price)} →{" "}
              </span>
              {formatCOP(s.suggested_price)}
            </>
          ) : (
            formatCOP(s.suggested_price)
          )}
        </span>
        <Badge variant={s.status === "applied" ? "success" : "muted"}>
          {s.status === "approved" ? "aprobada (pendiente de aplicar)" : s.status}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground">{range}</p>
      {s.rationale?.text && <p className="text-xs">{s.rationale.text}</p>}
      {s.confidence && (
        <p className="text-[10px] text-muted-foreground">
          Confianza: {Math.round(Number(s.confidence) * 100)}%
        </p>
      )}
      {PENDING.has(s.status) && (
        <div className="flex gap-2 pt-1">
          <Button onClick={onApply} disabled={busy}>
            Aprobar y aplicar
          </Button>
          <Button className="bg-muted text-foreground" onClick={onReject} disabled={busy}>
            Rechazar
          </Button>
        </div>
      )}
    </Card>
  );
}
