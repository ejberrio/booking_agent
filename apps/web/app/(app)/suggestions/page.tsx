"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { BatchPreviewDialog } from "@/components/suggestions/batch-preview-dialog";
import { SuggestionBlock } from "@/components/suggestions/suggestion-block";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { shortRange } from "@/lib/format";
import type { BatchResult } from "@/lib/types";

export default function SuggestionsPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["suggestions", "blocks"],
    queryFn: () => api.listSuggestionBlocks(),
  });
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [previewIds, setPreviewIds] = useState<number[] | null>(null);
  // Títulos congelados al abrir la vista previa: el resultado los conserva aunque la
  // lista se refresque (las aplicadas desaparecen de los bloques).
  const [titles, setTitles] = useState<Map<number, string>>(new Map());

  const blocks = useMemo(() => data?.blocks ?? [], [data]);
  // Título del bloque de origen y noches vendibles por sugerencia.
  const { titleById, nightsById } = useMemo(() => {
    const titles = new Map<number, string>();
    const nights = new Map<number, number>();
    for (const b of blocks) {
      for (const s of b.suggestions) {
        titles.set(
          s.id,
          b.kind === "event" ? b.title : `${b.title} · ${shortRange(b.date_from, b.date_to)}`,
        );
        nights.set(s.id, s.sellable_count);
      }
    }
    return { titleById: titles, nightsById: nights };
  }, [blocks]);

  // La selección solo conserva sugerencias que siguen visibles.
  const openPreview = (ids: number[]) => {
    setTitles(new Map(titleById));
    setPreviewIds(ids);
  };

  const visibleSelected = [...selected].filter((id) => titleById.has(id));
  const selectedNights = visibleSelected.reduce((acc, id) => acc + (nightsById.get(id) ?? 0), 0);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["suggestions"] });
    qc.invalidateQueries({ queryKey: ["calendar"] });
    qc.invalidateQueries({ queryKey: ["bookings"] });
  };

  const toggle = (ids: number[], checked: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      for (const id of ids) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });

  const reject = useMutation({
    mutationFn: (id: number) => api.rejectSuggestion(id),
    onSuccess: (_r, id) => {
      toast("Sugerencia rechazada");
      toggle([id], false);
    },
    onError: (e: Error) => toast.error(e.message),
    onSettled: refresh,
  });

  const onApplied = (r: BatchResult) => {
    const applied = Object.entries(r.suggestions)
      .filter(([, st]) => st === "applied")
      .map(([id]) => Number(id));
    toggle(applied, false);
    if (r.failed_count > 0) {
      toast.error(`${r.failed_count} noche(s) no se pudieron publicar; esas sugerencias siguen pendientes`);
    } else {
      toast.success(`${r.applied_count} noche(s) aplicadas y publicadas`);
    }
    refresh();
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4 pb-20">
      <h1 className="text-xl font-semibold">Sugerencias</h1>
      <p className="text-sm text-muted-foreground">
        Solo noches que todavía puedes vender, agrupadas por evento o periodo. Marca las que
        quieras y aplícalas juntas con una sola revisión.
      </p>

      {isError ? (
        <Card>
          <p className="text-sm text-red-500">No se pudieron cargar las sugerencias.</p>
        </Card>
      ) : isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : !blocks.length ? (
        <Card>
          <p className="text-sm text-muted-foreground">No hay sugerencias para noches libres.</p>
          {(data?.hidden_occupied ?? 0) > 0 && (
            <p className="mt-1 text-xs text-muted-foreground">
              {data?.hidden_occupied} noche(s) con sugerencia están ocultas por estar reservadas o
              bloqueadas.
            </p>
          )}
        </Card>
      ) : (
        <>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {blocks.length} bloque{blocks.length !== 1 ? "s" : ""}
              {(data?.hidden_occupied ?? 0) > 0 &&
                ` · ${data?.hidden_occupied} noche(s) ocultas (reservadas o bloqueadas)`}
            </span>
            {visibleSelected.length > 0 && (
              <button type="button" className="underline" onClick={() => setSelected(new Set())}>
                Quitar selección
              </button>
            )}
          </div>
          <div className="space-y-3">
            {blocks.map((b) => (
              <SuggestionBlock
                key={b.key}
                block={b}
                selected={selected}
                onToggle={toggle}
                onApplyOne={(id) => openPreview([id])}
                onRejectOne={(id) => reject.mutate(id)}
                busy={reject.isPending}
              />
            ))}
          </div>
        </>
      )}

      {visibleSelected.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 px-4 py-3 backdrop-blur md:left-56">
          <div className="mx-auto flex max-w-2xl items-center justify-between gap-3">
            <span className="text-sm">
              {visibleSelected.length} sugerencia{visibleSelected.length !== 1 ? "s" : ""} ·{" "}
              {selectedNights} noche{selectedNights !== 1 ? "s" : ""}
            </span>
            <Button onClick={() => openPreview(visibleSelected)}>Previsualizar</Button>
          </div>
        </div>
      )}

      <BatchPreviewDialog
        ids={previewIds}
        titleOf={(id) => titles.get(id) ?? titleById.get(id) ?? `Sugerencia ${id}`}
        onClose={() => setPreviewIds(null)}
        onApplied={onApplied}
      />
    </div>
  );
}
