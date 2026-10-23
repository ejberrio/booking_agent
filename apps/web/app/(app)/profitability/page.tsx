"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { UnitGate } from "@/components/account/unit-gate";
import { Kpi } from "@/components/dashboard/kpi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useActiveUnit } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { formatCOP, monthLabel } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { ProfitabilityMonth } from "@/lib/types";
import { cn } from "@/lib/utils";

// Rentabilidad mensual (feature 042): renta corta frente a un arriendo tradicional.
export default function ProfitabilityPage() {
  return (
    <UnitGate>
      <ProfitabilityContent />
    </UnitGate>
  );
}

const digits = (v: string) => v.replace(/\D/g, "");
const toNum = (v: string) => (v === "" ? null : Number(v));

function ProfitabilityContent() {
  const { m, lang } = useI18n();
  const t = m.profitability;
  const [unitTypeId] = useActiveUnit();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["profitability", unitTypeId], queryFn: () => api.profitability(unitTypeId) });
  const [rent, setRent] = useState("");
  const [fixed, setFixed] = useState("");
  const [cleaning, setCleaning] = useState("");

  useEffect(() => {
    const s = q.data?.settings;
    if (!s) return;
    setRent(s.reference_rent != null ? String(s.reference_rent) : "");
    setFixed(s.fixed_costs != null ? String(s.fixed_costs) : "");
    setCleaning(s.cleaning_per_stay != null ? String(s.cleaning_per_stay) : "");
  }, [q.data?.settings]);

  const save = useMutation({
    mutationFn: () =>
      api.saveProfitabilitySettings({
        unit_type_id: unitTypeId, reference_rent: toNum(rent), fixed_costs: toNum(fixed),
        cleaning_per_stay: toNum(cleaning),
      }),
    onSuccess: (data) => {
      qc.setQueryData(["profitability", unitTypeId], data);
      toast.success(t.saved);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (q.isLoading) return <Skeleton className="h-96" />;
  const d = q.data;
  if (!d) return null;
  const s = d.summary;
  const money = (v: number | null | undefined) => (v == null ? "·" : formatCOP(v, lang));
  const label = (key: string) => {
    const [y, mo] = key.split("-").map(Number);
    return monthLabel(y, mo - 1, lang);
  };
  const max = Math.max(1, ...d.months.map((r) => Math.abs(r.net)), s.rent_monthly ?? 0);

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold">{t.title}</h1>
        <p className="text-sm text-muted-foreground">{t.intro}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label={t.netAvg} value={money(s.net_monthly_avg)} hint={t.last12} />
        <Kpi
          label={t.vsRent}
          value={s.rent_monthly == null ? "·" : money(s.net_monthly_avg - s.rent_monthly)}
          hint={s.rent_monthly == null ? t.noRent : `${money(s.rent_monthly)} / ${m.profitability.month.toLowerCase()}`}
        />
        <Kpi label={t.occupancy} value={`${s.occupancy} %`} hint={t.last12} />
        <Kpi
          label={t.breakeven}
          value={s.breakeven_nights == null ? "·" : String(s.breakeven_nights)}
          hint={s.breakeven_nights == null ? t.noRent : t.breakevenHint(s.breakeven_nights)}
        />
      </div>

      <Card className="space-y-3">
        <div>
          <CardTitle>{t.settingsTitle}</CardTitle>
          <CardDescription>{t.settingsHint}</CardDescription>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {([
            [t.rent, rent, setRent],
            [t.fixed, fixed, setFixed],
            [t.cleaning, cleaning, setCleaning],
          ] as const).map(([lbl, val, set]) => (
            <label key={lbl} className="space-y-1 text-sm">
              <span className="font-medium">{lbl}</span>
              <Input inputMode="numeric" value={val} onChange={(e) => set(digits(e.target.value))} />
            </label>
          ))}
        </div>
        <Button onClick={() => save.mutate()} disabled={save.isPending}>{t.save}</Button>
      </Card>

      <Card className="space-y-3">
        <div className="flex items-end gap-1" style={{ height: 160 }} aria-hidden>
          {d.months.map((r) => (
            <Bar key={r.month} r={r} max={max} rent={s.rent_monthly} />
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="py-1 pr-2 font-normal">{t.month}</th>
                <th className="px-1 py-1 text-right font-normal">{t.nights}</th>
                <th className="px-1 py-1 text-right font-normal">{t.gross}</th>
                <th className="px-1 py-1 text-right font-normal">{t.commission}</th>
                <th className="px-1 py-1 text-right font-normal">{t.costs}</th>
                <th className="px-1 py-1 text-right font-normal">{t.net}</th>
                <th className="py-1 pl-1 text-right font-normal">{t.diff}</th>
              </tr>
            </thead>
            <tbody>
              {d.months.map((r) => (
                <tr key={r.month} className={cn("border-t border-border", r.future && "text-muted-foreground")}>
                  <td className="py-1 pr-2 whitespace-nowrap capitalize">
                    {label(r.month)}
                    {r.estimated && <Badge variant="warning" className="ml-1">{t.estimated}</Badge>}
                    {r.future && <span className="ml-1 text-[10px]">· {t.future}</span>}
                  </td>
                  <td className="px-1 py-1 text-right">{r.nights} <span className="text-muted-foreground">({r.occupancy} %)</span></td>
                  <td className="px-1 py-1 text-right">{money(r.gross)}</td>
                  <td className="px-1 py-1 text-right">{money(r.commission)}</td>
                  <td className="px-1 py-1 text-right">{money(r.cleaning + r.fixed)}</td>
                  <td className="px-1 py-1 text-right font-medium">{money(r.net)}</td>
                  <td className={cn("py-1 pl-1 text-right",
                    r.vs_rent != null && (r.vs_rent >= 0 ? "text-green-600" : "text-red-600"))}>
                    {money(r.vs_rent)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {d.months.every((r) => r.nights === 0) && <p className="text-sm text-muted-foreground">{t.empty}</p>}
        <p className="text-xs text-muted-foreground">
          {s.estimated && <>{t.estimatedHint} </>}
          {t.usdNote}
        </p>
      </Card>
    </div>
  );
}

function Bar({ r, max, rent }: { r: ProfitabilityMonth; max: number; rent: number | null }) {
  const h = (v: number) => `${Math.max(2, Math.round((Math.abs(v) / max) * 150))}px`;
  const good = rent == null ? r.net >= 0 : r.net >= rent;
  return (
    <div className="relative flex flex-1 flex-col items-center justify-end" title={r.month}>
      {rent != null && (
        <div className="absolute left-0 right-0 border-t border-dashed border-muted-foreground/60"
          style={{ bottom: h(rent) }} />
      )}
      <div
        className={cn("w-full max-w-6 rounded-t", r.future ? "bg-muted" : good ? "bg-green-500/70" : "bg-amber-500/70",
          r.net < 0 && "bg-red-500/60")}
        style={{ height: h(r.net) }}
      />
      <span className="mt-1 text-[9px] text-muted-foreground">{r.month.slice(5)}</span>
    </div>
  );
}
