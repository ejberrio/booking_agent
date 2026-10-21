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
import type { MarketFeedRun, PriceLabsListing } from "@/lib/types";

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

      <FeedSection city={city} bedrooms={bedrooms} bLabel={bLabel} />

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

/** Carga automática por la API de PriceLabs (feature 041). Usa el municipio y las habitaciones
 * de arriba; el anuncio se elige de la lista que devuelve PriceLabs. */
function FeedSection({ city, bedrooms, bLabel }: { city: string; bedrooms: number; bLabel: (n: number) => string }) {
  const { m, lang } = useI18n();
  const t = m.admin.market.api;
  const qc = useQueryClient();
  const feeds = useQuery({ queryKey: ["admin-market-feeds"], queryFn: api.marketFeeds });
  const [listings, setListings] = useState<PriceLabsListing[] | null>(null);
  const [picked, setPicked] = useState("");
  const after = (r: MarketFeedRun) => {
    qc.setQueryData(["admin-market-feeds"], r.feeds);
    qc.invalidateQueries({ queryKey: ["admin-market"] });
    if (r.result.ok) toast.success(`${r.result.imported} · ${r.result.from} – ${r.result.to}`);
    else toast.error(r.result.error ?? "PriceLabs");
  };
  const load = useMutation({
    mutationFn: api.pricelabsListings,
    onSuccess: setListings,
    onError: (e: Error) => toast.error(e.message),
  });
  const save = useMutation({
    mutationFn: () => {
      const li = listings?.find((l) => `${l.pms}|${l.id}` === picked);
      if (!li) throw new Error(t.pick);
      return api.saveMarketFeed({ city: city.trim(), bedrooms, listing_id: li.id, pms: li.pms });
    },
    onSuccess: after,
    onError: (e: Error) => toast.error(e.message),
  });
  const run = useMutation({ mutationFn: api.runMarketFeed, onSuccess: after, onError: (e: Error) => toast.error(e.message) });
  const remove = useMutation({
    mutationFn: api.deleteMarketFeed,
    onSuccess: (r) => qc.setQueryData(["admin-market-feeds"], r.feeds),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-3 border-t border-border pt-4">
      <div>
        <p className="text-sm font-medium">{t.title}</p>
        <p className="text-xs text-muted-foreground">{t.description}</p>
      </div>
      {listings === null ? (
        <Button className="bg-muted text-foreground" onClick={() => load.mutate()} disabled={load.isPending}>
          {t.load}
        </Button>
      ) : (
        <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
          <label className="space-y-1 text-sm">
            <span className="font-medium">{t.listing}</span>
            <select
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={picked}
              onChange={(e) => setPicked(e.target.value)}
            >
              <option value="">{t.pick}</option>
              {listings.map((l) => (
                <option key={`${l.pms}|${l.id}`} value={`${l.pms}|${l.id}`}>
                  {l.name ?? l.id} · {l.city ?? "?"}{l.bedrooms != null ? ` · ${l.bedrooms}` : ""}
                  {l.sync ? "" : ` · ${t.syncOff}`}
                </option>
              ))}
            </select>
          </label>
          <Button onClick={() => save.mutate()} disabled={!picked || city.trim().length < 2 || save.isPending}>
            {t.save} ({city.trim()} · {bLabel(bedrooms)})
          </Button>
        </div>
      )}
      {feeds.data && feeds.data.length === 0 && <p className="text-xs text-muted-foreground">{t.empty}</p>}
      {feeds.data && feeds.data.length > 0 && (
        <ul className="divide-y text-xs">
          {feeds.data.map((f) => (
            <li key={f.id} className="flex flex-wrap items-start gap-2 py-2">
              <div className="min-w-0 flex-1 space-y-0.5">
                <p className="font-medium capitalize">
                  {f.city} · {bLabel(f.bedrooms)} · <span className="font-normal normal-case">{f.pms}/{f.listing_id}</span>
                </p>
                <p className={f.last_status?.startsWith("error") ? "text-amber-600" : "text-muted-foreground"}>
                  {f.last_run_at ? `${dateTime(f.last_run_at, lang)} — ${f.last_status ?? ""}` : t.never}
                </p>
              </div>
              <Button className="bg-muted text-foreground" onClick={() => run.mutate(f.id)} disabled={run.isPending}>
                {t.run}
              </Button>
              <Button
                className="bg-muted text-foreground"
                disabled={remove.isPending}
                onClick={() => window.confirm(t.confirmRemove) && remove.mutate(f.id)}
              >
                {t.remove}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
