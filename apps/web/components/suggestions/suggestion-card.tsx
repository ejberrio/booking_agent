"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatCOP } from "@/lib/format";
import type { Suggestion } from "@/lib/types";

interface Props {
  suggestion: Suggestion;
  onApprove: () => void;
  onReject: () => void;
  onApply: () => void;
  busy?: boolean;
}

export function SuggestionCard({ suggestion: s, onApprove, onReject, onApply, busy }: Props) {
  const range = s.date_from === s.date_to ? s.date_from : `${s.date_from} → ${s.date_to}`;
  return (
    <Card className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{formatCOP(s.suggested_price)}</span>
        <Badge variant={s.status === "applied" ? "success" : "muted"}>{s.status}</Badge>
      </div>
      <p className="text-xs text-muted-foreground">{range}</p>
      {s.rationale?.text && <p className="text-xs">{s.rationale.text}</p>}
      {s.confidence && (
        <p className="text-[10px] text-muted-foreground">
          Confianza: {Math.round(Number(s.confidence) * 100)}%
        </p>
      )}
      {s.status === "proposed" && (
        <div className="flex gap-2 pt-1">
          <Button onClick={onApply} disabled={busy}>
            Aplicar
          </Button>
          <Button className="bg-muted text-foreground" onClick={onApprove} disabled={busy}>
            Aprobar
          </Button>
          <Button className="bg-muted text-foreground" onClick={onReject} disabled={busy}>
            Rechazar
          </Button>
        </div>
      )}
    </Card>
  );
}
