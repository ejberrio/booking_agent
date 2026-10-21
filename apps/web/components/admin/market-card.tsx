"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { dateTime, formatCOP, shortDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

const STALE_DAYS = 35;
const ENDS_SOON_DAYS = 60;
const BEDROOMS = [0, 1, 2, 3, 4, 5, 6];

const daysSince = (iso: string) => (Date.now() - new Date(iso).getTime()) / 86_400_000;

/** Mercado (feature 040): el administrador sube el CSV de PriceLabs → "Precios Futuros". */
export function MarketCard() {
  const { m, lang } = useI18n();
  const t = m.admin.market;
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-market"], queryFn: api.marketBands });
  const [city, setCity] = useState("Medellín");
  const [bedrooms, setBedrooms] = useState(3);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error(t.file);
      return api.uploadMarketCsv({ city: city.trim(), bedrooms, csv: await file.text() });
    },
    onSuccess: (r) => {
      setResult(`${t.loaded(r.imported, r.from, r.to)} ${t.skipped(r.past, r.invalid)}`);
      toast.success(t.loaded(r.imported, r.from, r.to));
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      qc.setQueryData(["admin-market"], r.bands);
    },
    onError: (e: Error) => {
      setResult(null);
      toast.error(e.message);
    },
  });
  const remove = useMutation({
    mutationFn: (b: { city: string; bedrooms: number }) => api.deleteMarketBands(b.city, b.bedrooms),
    onSuccess: () => {
      toast(t.removed);
      qc.invalidateQueries({ queryKey: ["admin-market"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const bLabel = (n: number) => (n === 0 ? t.allBedrooms : String(n));

  return (
    <Card className="space-y-4">
      <div>
        <CardTitle>{t.title}</CardTitle>
        <CardDescription>{t.description}</CardDescription>
      </div>

      <ol className="list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
        {t.steps.map((s) => <li key={s}>{s}</li>)}
      </ol>

      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <label className="space-y-1 text-sm">
          <span className="font-medium">{t.city}</span>
          <Input value={city} onChange={(e) => setCity(e.target.value)} maxLength={80} />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">{t.bedrooms}</span>
          <select
            className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm sm:w-28"
            value={bedrooms}
            onChange={(e) => setBedrooms(Number(e.target.value))}
          >
            {BEDROOMS.map((n) => <option key={n} value={n}>{bLabel(n)}</option>)}
          </select>
        </label>
      </div>
      <label className="block space-y-1 text-sm">
        <span className="font-medium">{t.file}</span>
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-2 file:text-foreground"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>
      <Button onClick={() => upload.mutate()} disabled={!file || city.trim().length < 2 || upload.isPending}>
        {upload.isPending ? t.uploading : t.upload}
      </Button>
      {result && <p className="text-sm text-muted-foreground">{result}</p>}

      {q.data && q.data.length === 0 && <p className="text-sm text-muted-foreground">{t.empty}</p>}
      {q.data && q.data.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="py-1 pr-2 font-normal">{t.zone}</th>
                <th className="px-1 py-1 font-normal">{t.bedrooms}</th>
                <th className="px-1 py-1 font-normal">{t.range}</th>
                <th className="px-1 py-1 text-right font-normal">{t.median}</th>
                <th className="px-1 py-1 font-normal">{t.updated}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {q.data.map((b) => {
                const stale = !b.updated_at || daysSince(b.updated_at) > STALE_DAYS;
                const endsSoon = -daysSince(`${b.to}T00:00:00`) < ENDS_SOON_DAYS;
                return (
                  <tr key={`${b.city}-${b.bedrooms}-${b.source}`} className="border-t border-border align-top">
                    <td className="py-1 pr-2 capitalize">{b.city}</td>
                    <td className="px-1 py-1">{bLabel(b.bedrooms)}</td>
                    <td className="px-1 py-1 whitespace-nowrap">
                      {shortDate(b.from, lang)} – {shortDate(b.to, lang)}
                      {endsSoon && <Badge variant="warning" className="ml-1">{t.endsSoon}</Badge>}
                    </td>
                    <td className="px-1 py-1 text-right">{b.p50_avg ? formatCOP(b.p50_avg, lang) : "·"}</td>
                    <td className="px-1 py-1">
                      {b.updated_at ? dateTime(b.updated_at, lang) : "·"}
                      {stale && <Badge variant="warning" className="ml-1">{t.stale}</Badge>}
                    </td>
                    <td className="py-1 pl-1 text-right">
                      <Button
                        className="bg-muted text-foreground"
                        disabled={remove.isPending}
                        onClick={() => {
                          if (window.confirm(t.confirmRemove(b.city, bLabel(b.bedrooms)))) {
                            remove.mutate({ city: b.city, bedrooms: b.bedrooms });
                          }
                        }}
                      >
                        {t.remove}
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
