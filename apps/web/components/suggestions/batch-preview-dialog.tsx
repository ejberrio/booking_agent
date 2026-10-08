"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatCOP, formatNumber, shortDate } from "@/lib/format";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { trServer } from "@/lib/i18n/server-messages";
import type { BatchResult } from "@/lib/types";

interface Props {
  ids: number[] | null; // null = cerrado
  titleOf: (suggestionId: number) => string; // bloque/evento de origen
  onClose: () => void;
  onApplied: (r: BatchResult) => void;
}

const STATUS_LABEL = { applied: "statusApplied", skipped: "statusSkipped", failed: "statusFailed" } as const;
/** Error de la API cuando la vista previa quedó obsoleta (llega ya traducido por req()). */
const STALE_ES = "La vista previa cambió (precios, reservas o sugerencias); revísala de nuevo.";
const STATUS_CLASS = {
  applied: "text-emerald-600",
  skipped: "text-muted-foreground",
  failed: "text-red-500",
} as const;

/** Vista previa ÚNICA del lote + confirmación explícita (Principio III, feature 019). */
export function BatchPreviewDialog({ ids, titleOf, onClose, onApplied }: Props) {
  const { m } = useI18n();
  const t = m.suggestions;
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
  const errMsg = apply.error?.message;
  const stale = !!errMsg && (errMsg.includes("revísala") || errMsg === trServer(STALE_ES));
  const result = apply.data;
  const willPublish = t.willPublish(preview.data?.valid_count ?? 0);

  return (
    <Dialog open={open} onClose={close} className="max-w-2xl">
      <h2 className="text-base font-semibold">
        {result ? t.resultTitle : t.previewTitle}
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
            {willPublish[0] && `${willPublish[0]} `}
            <strong className="text-foreground">{preview.data.valid_count}</strong> {willPublish[1]}
            {preview.data.skipped_count > 0 && <> · {t.skippedNote(preview.data.skipped_count)}</>}
            .
          </p>
          {preview.data.items.some((i) => i.mode === "promotion" && i.valid) && (
            <div className="mt-2 space-y-1 rounded-md bg-muted/50 p-2 text-xs text-muted-foreground">
              <p>{t.promoExplain}</p>
              {preview.data.min_price ? (
                <p>{t.minPriceNote(formatCOP(preview.data.min_price))}</p>
              ) : (
                <p className="text-amber-600">
                  {t.noMinPrice}{" "}
                  <Link href="/settings" className="underline">
                    {t.setMinPrice}
                  </Link>
                </p>
              )}
              {preview.data.conditional_deals.length > 0 && (
                <p>
                  {t.conditionalDeals(
                    preview.data.conditional_deals
                      .map((d) => `${d.name} (${d.channel === "booking" ? "Booking.com" : "Airbnb"}, ${Number(d.pct)}%)`)
                      .join(", "),
                  )}
                </p>
              )}
              {preview.data.overlaps.length > 0 && (
                <p className="text-amber-600">{t.overlapsWarn(preview.data.overlaps.join(", "))}</p>
              )}
            </div>
          )}
          <div className="mt-3 max-h-[50vh] overflow-y-auto rounded-md border border-border">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-card text-left text-muted-foreground">
                <tr>
                  <th className="px-2 py-1.5 font-medium">{t.colNight}</th>
                  <th className="px-2 py-1.5 font-medium">{t.colSource}</th>
                  <th className="px-2 py-1.5 font-medium">{t.colChange}</th>
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
                        {i.valid && i.mode === "promotion" ? (
                          <span className="flex flex-col gap-0.5">
                            <span className="inline-flex flex-wrap items-center gap-1">
                              {formatCOP(i.old_price)} →{" "}
                              <strong>{formatCOP(i.promo_price)}</strong>
                              <ArrowDown size={12} className="text-orange-500" />
                              <span className="rounded bg-orange-500/15 px-1 text-[10px] text-orange-600">
                                {t.modePromo(formatNumber(Number(i.promo_pct)))}
                              </span>
                            </span>
                            {Object.keys(i.final_by_channel).length > 0 && (
                              <span className="text-[10px] text-muted-foreground">
                                {t.mobileShort}:{" "}
                                {Object.entries(i.final_by_channel)
                                  .map(([ch, v]) => `${ch === "booking" ? "Booking" : "Airbnb"} ${formatCOP(v)}`)
                                  .join(" · ")}
                              </span>
                            )}
                            {i.clipped && <span className="text-[10px] text-amber-600">{t.clipped}</span>}
                          </span>
                        ) : i.valid ? (
                          <span className="inline-flex items-center gap-1">
                            {formatCOP(i.old_price)} →{" "}
                            <strong>{formatCOP(i.new_price)}</strong>
                            {up && <ArrowUp size={12} className="text-emerald-600" />}
                            {down && <ArrowDown size={12} className="text-orange-500" />}
                            <span className="text-[10px] text-muted-foreground">({t.modeBase})</span>
                          </span>
                        ) : (
                          <span>{t.skippedReason(trServer(i.reason))}</span>
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
          <Button onClick={close}>{m.common.done}</Button>
        ) : (
          <>
            <Button className="bg-muted text-foreground" onClick={close} disabled={apply.isPending}>
              {m.common.cancel}
            </Button>
            {stale ? (
              <Button
                onClick={() => {
                  apply.reset();
                  preview.refetch();
                }}
              >
                {t.previewAgain}
              </Button>
            ) : (
              <Button
                onClick={() => apply.mutate()}
                disabled={apply.isPending || !preview.data || preview.data.valid_count === 0}
              >
                {apply.isPending ? t.publishing : t.confirmPublish}
              </Button>
            )}
          </>
        )}
      </div>
    </Dialog>
  );
}

function ResultView({ result, titleOf }: { result: BatchResult; titleOf: (id: number) => string }) {
  const t = useI18n().m.suggestions;
  return (
    <>
      <p className="mt-1 text-sm">
        <span className="text-emerald-600">{t.resultApplied(result.applied_count)}</span>
        {result.skipped_count > 0 && <> · {t.resultSkipped(result.skipped_count)}</>}
        {result.failed_count > 0 && (
          <span className="text-red-500"> · {t.resultFailed(result.failed_count)}</span>
        )}
        {result.promotions.length > 0 && <> · {t.promotionsCreated(result.promotions.length)}</>}
      </p>
      <ul className="mt-3 max-h-[50vh] space-y-1 overflow-y-auto text-xs">
        {result.nights.map((n) => (
          <li key={`${n.date}-${n.suggestion_id}`} className="flex justify-between gap-2">
            <span>
              {shortDate(n.date)} · <span className="text-muted-foreground">{titleOf(n.suggestion_id)}</span>
            </span>
            <span className={STATUS_CLASS[n.status]}>
              {t[STATUS_LABEL[n.status]]}
              {n.reason ? ` (${trServer(n.reason)})` : ""}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}
