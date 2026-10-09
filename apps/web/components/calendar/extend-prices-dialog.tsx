"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatCOP, monthLabel } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { trServer } from "@/lib/i18n/server-messages";
import type { ExtensionParams, ExtensionResult } from "@/lib/types";

interface Props {
  open: boolean;
  unitTypeId: number;
  defaultUntil?: string;
  maxUntil?: string;
  onClose: () => void;
}

type Override = { price?: number | null; included: boolean };

/** Mensaje de la API cuando la huella no coincide (llega ya traducido por req()). */
const STALE_ES = "la vista previa quedó desactualizada; vuelve a previsualizar";

const STATUS_CLASS = {
  applied: "text-emerald-600",
  skipped: "text-muted-foreground",
  failed: "text-red-500",
} as const;

function label(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return monthLabel(y, m - 1);
}

/** Extender precios (feature 023): plantilla por mes editable → vista previa → confirmación reforzada. */
export function ExtendPricesDialog({ open, unitTypeId, defaultUntil, maxUntil, onClose }: Props) {
  const { m } = useI18n();
  const t = m.extension;
  const qc = useQueryClient();
  const [until, setUntil] = useState(defaultUntil ?? "");
  const [weekendPct, setWeekendPct] = useState(0);
  const [openClosed, setOpenClosed] = useState(true);
  const [overrides, setOverrides] = useState<Record<string, Override>>({});
  const [ack, setAck] = useState(false);
  const [staleNote, setStaleNote] = useState(false);

  const draft: ExtensionParams = {
    unit_type_id: unitTypeId,
    ...(until ? { until } : {}),
    weekend_pct: weekendPct,
    open_closed: openClosed,
    ...(Object.keys(overrides).length
      ? { months: Object.entries(overrides).map(([month, o]) => ({ month, ...o })) }
      : {}),
  };
  const [committed, setCommitted] = useState<ExtensionParams>(draft);
  const dirty = JSON.stringify(draft) !== JSON.stringify(committed);

  const preview = useQuery({
    queryKey: ["extension-preview", committed],
    queryFn: () => api.previewExtension(committed),
    enabled: open,
    gcTime: 0,
    staleTime: 0,
  });
  const apply = useMutation({
    mutationFn: () => api.applyExtension(committed, preview.data?.fingerprint ?? ""),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["calendar"] });
      qc.invalidateQueries({ queryKey: ["horizon-status"] });
    },
    onError: (e: Error) => {
      if (e.message === trServer(STALE_ES)) {
        setStaleNote(true);
        setAck(false);
        preview.refetch();
      }
    },
  });

  const close = () => {
    apply.reset();
    setAck(false);
    setStaleNote(false);
    onClose();
  };
  const setOverride = (month: string, patch: Partial<Override>, current: Override) =>
    setOverrides((o) => ({ ...o, [month]: { ...current, ...o[month], ...patch } }));

  const data = preview.data;
  const result = apply.data;

  return (
    <Dialog open={open} onClose={close} className="max-w-3xl">
      <h2 className="text-base font-semibold">{result ? t.resultTitle : t.title}</h2>
      {result ? (
        <ResultView result={result} />
      ) : (
        <>
          <p className="mt-1 text-sm text-muted-foreground">{t.intro}</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <label className="text-xs">
              <span className="text-muted-foreground">{t.until}</span>
              <Input
                type="date"
                value={until}
                max={maxUntil}
                onChange={(e) => setUntil(e.target.value)}
              />
            </label>
            <label className="text-xs">
              <span className="text-muted-foreground">{t.weekendPct}</span>
              <Input
                type="number"
                min={0}
                max={50}
                value={weekendPct}
                onChange={(e) => setWeekendPct(Math.max(0, Math.min(50, Number(e.target.value) || 0)))}
              />
            </label>
            <label className="flex items-start gap-2 pt-4 text-xs">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={openClosed}
                onChange={(e) => setOpenClosed(e.target.checked)}
              />
              <span>
                {t.openClosed}
                <span className="block text-muted-foreground">{t.openClosedHint}</span>
              </span>
            </label>
          </div>

          {preview.isLoading ? (
            <Skeleton className="mt-3 h-48 w-full" />
          ) : preview.isError ? (
            <p className="mt-3 text-sm text-red-500">{(preview.error as Error).message}</p>
          ) : data && data.months.length === 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">{t.nothing}</p>
          ) : data ? (
            <>
              <div className="mt-3 max-h-[45vh] overflow-y-auto rounded-md border border-border">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-card text-left text-muted-foreground">
                    <tr>
                      <th className="px-2 py-1.5 font-medium">{t.include}</th>
                      <th className="px-2 py-1.5 font-medium">{t.colMonth}</th>
                      <th className="px-2 py-1.5 font-medium">{t.colPrice}</th>
                      <th className="px-2 py-1.5 font-medium">{t.colNights}</th>
                      <th className="px-2 py-1.5 font-medium">{t.colDetail}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.months.map((mo) => {
                      const current: Override = {
                        price: mo.price === null ? null : Number(mo.price),
                        included: mo.included,
                      };
                      const ov = { ...current, ...overrides[mo.month] };
                      return (
                        <tr
                          key={mo.month}
                          className={`border-t border-border align-top ${ov.included ? "" : "text-muted-foreground"}`}
                        >
                          <td className="px-2 py-1.5">
                            <input
                              type="checkbox"
                              checked={ov.included}
                              aria-label={`${t.include} ${label(mo.month)}`}
                              onChange={(e) => setOverride(mo.month, { included: e.target.checked }, current)}
                            />
                          </td>
                          <td className="whitespace-nowrap px-2 py-1.5">{label(mo.month)}</td>
                          <td className="px-2 py-1.5">
                            <Input
                              type="number"
                              min={1}
                              step={1000}
                              className="h-7 w-28 text-xs"
                              value={ov.price ?? ""}
                              disabled={!ov.included}
                              onChange={(e) =>
                                setOverride(
                                  mo.month,
                                  { price: e.target.value === "" ? null : Number(e.target.value) },
                                  current,
                                )
                              }
                            />
                            {mo.proposed_price !== null && (
                              <span className="mt-0.5 block text-[10px] text-muted-foreground">
                                {t.proposed(formatCOP(mo.proposed_price))}
                              </span>
                            )}
                          </td>
                          <td className="px-2 py-1.5">{mo.nights}</td>
                          <td className="px-2 py-1.5">
                            <span className="flex flex-col gap-0.5">
                              {mo.weekday_price !== null && <span>{formatCOP(mo.weekday_price)}</span>}
                              {mo.weekend_price !== null && mo.weekend_price !== mo.weekday_price && (
                                <span>{t.weekendShort(formatCOP(mo.weekend_price))}</span>
                              )}
                              {mo.to_open > 0 && <span className="text-emerald-600">{t.toOpen(mo.to_open)}</span>}
                              {mo.kept_closed > 0 && (
                                <span className="text-muted-foreground">{t.keptClosed(mo.kept_closed)}</span>
                              )}
                              {mo.clipped_min > 0 && (
                                <span className="text-amber-600">{t.clippedMin(mo.clipped_min)}</span>
                              )}
                              {mo.clipped_max > 0 && (
                                <span className="text-amber-600">{t.clippedMax(mo.clipped_max)}</span>
                              )}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                <p>{data.min_price ? t.minNote(formatCOP(data.min_price)) : t.noMin}</p>
                <p className="text-sm text-foreground">{t.totals(data.total_nights, data.total_to_open)}</p>
              </div>
            </>
          ) : null}

          {dirty && <p className="mt-2 text-xs text-amber-600">{t.editedHint}</p>}
          {staleNote && <p className="mt-2 text-xs text-amber-600">{t.stale}</p>}
          {apply.isError && apply.error.message !== trServer(STALE_ES) && (
            <p className="mt-2 text-xs text-red-500">{apply.error.message}</p>
          )}

          {data && data.total_nights > 0 && !dirty && (
            <label className="mt-3 flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={ack} onChange={(e) => setAck(e.target.checked)} />
              <span>{t.confirmCheck(data.total_nights)}</span>
            </label>
          )}

          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <Button className="bg-muted text-foreground" onClick={close}>
              {t.cancel}
            </Button>
            <Button
              className="bg-muted text-foreground"
              disabled={!dirty || preview.isFetching}
              onClick={() => {
                setAck(false);
                setStaleNote(false);
                setCommitted(draft);
              }}
            >
              {t.refresh}
            </Button>
            <Button
              disabled={!data || data.total_nights === 0 || dirty || !ack || apply.isPending || preview.isFetching}
              onClick={() => apply.mutate()}
            >
              {t.confirm}
            </Button>
          </div>
        </>
      )}
      {result && (
        <div className="mt-4 flex justify-end">
          <Button onClick={close}>{t.close}</Button>
        </div>
      )}
    </Dialog>
  );
}

function ResultView({ result }: { result: ExtensionResult }) {
  const { m } = useI18n();
  const t = m.extension;
  const statusLabel = { applied: t.statusApplied, failed: t.statusFailed, skipped: t.statusSkipped };
  return (
    <>
      <p className="mt-1 text-sm">{t.resultSummary(result.applied_nights, result.opened_nights)}</p>
      <ul className="mt-3 space-y-1 text-xs">
        {result.months.map((r) => (
          <li key={r.month} className="flex flex-wrap gap-2">
            <span className="w-32">{label(r.month)}</span>
            <span className={STATUS_CLASS[r.status]}>{statusLabel[r.status]}</span>
            {r.status === "applied" && (
              <span className="text-muted-foreground">{t.resultSummary(r.nights, r.opened)}</span>
            )}
            {r.detail && (
              <span className={r.status === "applied" ? "text-amber-600" : "text-red-500"}>
                {trServer(r.detail)}
              </span>
            )}
          </li>
        ))}
      </ul>
      {result.failed_months > 0 && <p className="mt-2 text-xs text-amber-600">{t.failedNote}</p>}
    </>
  );
}
