"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatCOP, shortDate } from "@/lib/format";
import type { BatchResult } from "@/lib/types";

interface Props {
  ids: number[] | null; // null = cerrado
  titleOf: (suggestionId: number) => string; // bloque/evento de origen
  onClose: () => void;
  onApplied: (r: BatchResult) => void;
}

const STATUS_LABEL = { applied: "aplicada", skipped: "omitida", failed: "falló" } as const;
const STATUS_CLASS = {
  applied: "text-emerald-600",
  skipped: "text-muted-foreground",
  failed: "text-red-500",
} as const;

/** Vista previa ÚNICA del lote + confirmación explícita (Principio III, feature 019). */
export function BatchPreviewDialog({ ids, titleOf, onClose, onApplied }: Props) {
  const open = ids !== null && ids.length > 0;
  const preview = useQuery({
    queryKey: ["suggestion-batch-preview", ids],
    queryFn: () => api.previewSuggestionBatch(ids ?? []),
    enabled: open,
    gcTime: 0,
    staleTime: 0,
  });
  const apply = useMutation({
    mutationFn: () => api.applySuggestionBatch(ids ?? [], preview.data?.fingerprint ?? ""),
    onSuccess: (r) => onApplied(r),
  });

  const close = () => {
    apply.reset();
    onClose();
  };
  const stale = apply.error?.message.includes("revísala");
  const result = apply.data;

  return (
    <Dialog open={open} onClose={close} className="max-w-2xl">
      <h2 className="text-base font-semibold">
        {result ? "Resultado" : "Vista previa de los cambios"}
      </h2>

      {preview.isLoading ? (
        <Skeleton className="mt-3 h-40 w-full" />
      ) : preview.isError ? (
        <p className="mt-3 text-sm text-red-500">{(preview.error as Error).message}</p>
      ) : result ? (
        <ResultView result={result} titleOf={titleOf} />
      ) : preview.data ? (
        <>
          <p className="mt-1 text-sm text-muted-foreground">
            Se publicarán <strong className="text-foreground">{preview.data.valid_count}</strong>{" "}
            noche{preview.data.valid_count !== 1 ? "s" : ""} en Booking.com y Airbnb
            {preview.data.skipped_count > 0 && (
              <> · {preview.data.skipped_count} se omiten (ver motivo)</>
            )}
            .
          </p>
          <div className="mt-3 max-h-[50vh] overflow-y-auto rounded-md border border-border">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-card text-left text-muted-foreground">
                <tr>
                  <th className="px-2 py-1.5 font-medium">Noche</th>
                  <th className="px-2 py-1.5 font-medium">Origen</th>
                  <th className="px-2 py-1.5 font-medium">Antes → después</th>
                </tr>
              </thead>
              <tbody>
                {preview.data.items.map((i) => {
                  const up = i.old_price !== null && Number(i.new_price) > Number(i.old_price);
                  const down = i.old_price !== null && Number(i.new_price) < Number(i.old_price);
                  return (
                    <tr
                      key={`${i.date}-${i.suggestion_id}`}
                      className={`border-t border-border ${i.valid ? "" : "text-muted-foreground"}`}
                    >
                      <td className="px-2 py-1.5 whitespace-nowrap">{shortDate(i.date)}</td>
                      <td className="max-w-[10rem] truncate px-2 py-1.5">{titleOf(i.suggestion_id)}</td>
                      <td className="px-2 py-1.5">
                        {i.valid ? (
                          <span className="inline-flex items-center gap-1">
                            {formatCOP(i.old_price)} →{" "}
                            <strong>{formatCOP(i.new_price)}</strong>
                            {up && <ArrowUp size={12} className="text-emerald-600" />}
                            {down && <ArrowDown size={12} className="text-orange-500" />}
                          </span>
                        ) : (
                          <span>omitida: {i.reason}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {apply.isError && (
            <p className="mt-3 text-sm text-red-500">{apply.error.message}</p>
          )}
        </>
      ) : null}

      <div className="mt-4 flex justify-end gap-2">
        {result ? (
          <Button onClick={close}>Listo</Button>
        ) : (
          <>
            <Button className="bg-muted text-foreground" onClick={close} disabled={apply.isPending}>
              Cancelar
            </Button>
            {stale ? (
              <Button
                onClick={() => {
                  apply.reset();
                  preview.refetch();
                }}
              >
                Volver a previsualizar
              </Button>
            ) : (
              <Button
                onClick={() => apply.mutate()}
                disabled={apply.isPending || !preview.data || preview.data.valid_count === 0}
              >
                {apply.isPending ? "Publicando…" : "Confirmar y publicar"}
              </Button>
            )}
          </>
        )}
      </div>
    </Dialog>
  );
}

function ResultView({ result, titleOf }: { result: BatchResult; titleOf: (id: number) => string }) {
  return (
    <>
      <p className="mt-1 text-sm">
        <span className="text-emerald-600">{result.applied_count} aplicadas</span>
        {result.skipped_count > 0 && <> · {result.skipped_count} omitidas</>}
        {result.failed_count > 0 && (
          <span className="text-red-500"> · {result.failed_count} fallaron (siguen pendientes)</span>
        )}
      </p>
      <ul className="mt-3 max-h-[50vh] space-y-1 overflow-y-auto text-xs">
        {result.nights.map((n) => (
          <li key={`${n.date}-${n.suggestion_id}`} className="flex justify-between gap-2">
            <span>
              {shortDate(n.date)} · <span className="text-muted-foreground">{titleOf(n.suggestion_id)}</span>
            </span>
            <span className={STATUS_CLASS[n.status]}>
              {STATUS_LABEL[n.status]}
              {n.reason ? ` (${n.reason})` : ""}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}
