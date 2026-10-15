"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const KEYS = ["visit", "report", "report_cached", "city_search", "signup_open", "signup_from_report", "waitlist"];

/** Beta pública (feature 030): registro abierto con cupo, presupuesto, métricas y lista de espera. */
export function BetaCard() {
  const { m } = useI18n();
  const t = m.pub.admin;
  const reg = m.admin.registration;
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-beta"], queryFn: api.adminBeta });
  const [quota, setQuota] = useState("");
  const [budget, setBudget] = useState("");
  useEffect(() => {
    if (q.data) {
      setQuota(String(q.data.quota));
      setBudget(String(q.data.city_budget));
    }
  }, [q.data]);
  const refresh = () => qc.invalidateQueries({ queryKey: ["admin-beta"] });
  const patch = useMutation({
    mutationFn: api.patchBeta,
    onSuccess: () => {
      toast.success(t.saved);
      refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const invite = useMutation({
    mutationFn: api.inviteWaitlist,
    onSuccess: () => {
      toast.success(t.invited);
      refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const remove = useMutation({
    mutationFn: api.deleteWaitlist,
    onSuccess: refresh,
    onError: (e: Error) => toast.error(e.message),
  });

  const d = q.data;
  if (!d) return null;
  const days = Array.from(new Set(d.metrics.map((r) => r.day))).sort().reverse();
  const val = (day: string, key: string) => d.metrics.find((r) => r.day === day && r.key === key)?.value ?? 0;

  return (
    <Card className="space-y-4">
      <div>
        <CardTitle>{t.title}</CardTitle>
        <CardDescription>{t.description}</CardDescription>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">{t.enabled}</p>
        <div className="flex gap-2">
          <Button className={d.enabled ? "" : "bg-muted text-foreground"}
            onClick={() => patch.mutate({ enabled: true })} disabled={patch.isPending || d.enabled}>
            {reg.on}
          </Button>
          <Button className={!d.enabled ? "" : "bg-muted text-foreground"}
            onClick={() => patch.mutate({ enabled: false })} disabled={patch.isPending || !d.enabled}>
            {reg.off}
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className="font-medium">{t.quota}</span>
          <Input inputMode="numeric" value={quota} onChange={(e) => setQuota(e.target.value.replace(/\D/g, ""))} />
          <span className="block text-xs text-muted-foreground">{t.used(d.used, d.quota)}</span>
          {d.full && <span className="block text-xs text-amber-600">{t.full}</span>}
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">{t.budget}</span>
          <Input inputMode="numeric" value={budget} onChange={(e) => setBudget(e.target.value.replace(/\D/g, ""))} />
          <span className="block text-xs text-muted-foreground">
            {t.searchesToday(d.searches_today, d.city_budget)} · {t.reportsTotal(d.reports_total)}
          </span>
        </label>
      </div>
      <Button onClick={() => patch.mutate({ quota: Number(quota) || 0, city_budget: Number(budget) || 0 })}
        disabled={patch.isPending}>
        {t.save}
      </Button>

      <div className="space-y-2">
        <p className="text-sm font-medium">{t.metricsTitle}</p>
        {days.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t.noMetrics}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="py-1 pr-2 font-normal">{t.day}</th>
                  {KEYS.map((k) => <th key={k} className="px-1 py-1 text-right font-normal">{t.keys[k]}</th>)}
                </tr>
              </thead>
              <tbody>
                {days.map((day) => (
                  <tr key={day} className="border-t border-border">
                    <td className="py-1 pr-2 whitespace-nowrap">{day}</td>
                    {KEYS.map((k) => <td key={k} className="px-1 py-1 text-right">{val(day, k) || "·"}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">{t.waitlistTitle}</p>
        {d.waitlist.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t.waitlistEmpty}</p>
        ) : (
          <ul className="divide-y text-sm">
            {d.waitlist.map((w) => (
              <li key={w.id} className="flex flex-wrap items-center gap-2 py-2">
                <span className="min-w-0 flex-1 truncate">
                  {w.email}
                  <span className="text-muted-foreground">
                    {w.municipality ? ` · ${w.municipality}` : ""} · {w.language}
                  </span>
                </span>
                <Button onClick={() => invite.mutate(w.id)} disabled={invite.isPending}>{t.invite}</Button>
                <Button className="bg-muted text-foreground" onClick={() => remove.mutate(w.id)}
                  disabled={remove.isPending}>
                  {t.remove}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
