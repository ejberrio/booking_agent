"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Beds24Rooms } from "@/lib/types";
import { cn } from "@/lib/utils";

// Asistente «Conectar Beds24» (feature 044, #150): generar código → pegar → elegir → importar.
const BEDS24_URL = "https://beds24.com/control3.php";
const GUIDE = {
  airbnb: "https://wiki.beds24.com/index.php/Connect_Airbnb_Account",
  booking: "https://wiki.beds24.com/index.php/Booking.com:_Synchronise_bookings_prices_availability",
};
const READ = ["bookings", "bookings-personal", "inventory", "properties", "channels"];
const WRITE = ["inventory", "channels"];

type Step = 1 | 2 | 3 | 4;

export default function ConnectPage() {
  const { m, lang } = useI18n();
  const t = m.connection;
  const qc = useQueryClient();
  const info = useQuery({ queryKey: ["connection"], queryFn: api.connection });
  const [step, setStep] = useState<Step | null>(null);
  const [code, setCode] = useState("");
  const [rooms, setRooms] = useState<Beds24Rooms | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [links, setLinks] = useState<Record<number, string>>({});

  const fromRooms = (r: Beds24Rooms) => {
    setRooms(r);
    const sel = r.properties.flatMap((p) => p.rooms.filter((x) => x.selected).map((x) => x.id));
    setPicked(new Set(sel));
    // Modo sin conexión: propone asociar cada apartamento con una habitación, en orden.
    setLinks(Object.fromEntries((r.manual_units ?? []).map((u, i) => [u.id, sel[i] ?? ""])));
  };
  const redeem = useMutation({
    mutationFn: () => api.redeemConnection(code.trim()),
    onSuccess: (r) => {
      fromRooms(r);
      setCode("");
      setStep(3);
      qc.invalidateQueries({ queryKey: ["connection"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const loadRooms = useMutation({
    mutationFn: api.beds24Rooms,
    onSuccess: (r) => {
      fromRooms(r);
      setStep(3);
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const importRemote = useMutation({
    mutationFn: () => api.importRemote(),
    onError: () => toast.error(t.step4.failed),
    onSettled: () => qc.invalidateQueries(),
  });
  const save = useMutation({
    mutationFn: async () => {
      if (!rooms) throw new Error(t.step3.none);
      const allIds = rooms.properties.filter((p) => !p.taken).flatMap((p) => p.rooms.map((r) => r.id));
      const ids = allIds.filter((id) => picked.has(id));
      if (ids.length === 0) throw new Error(t.step3.none);
      const manual = rooms.manual_units ?? [];
      if (manual.length > 0) {
        const chosen = manual.map((u) => links[u.id]);
        if (chosen.some((r) => !r || !picked.has(r)) || new Set(chosen).size !== chosen.length) {
          throw new Error(t.link.missing);
        }
        await api.linkManual(ids, links);
        return;
      }
      await api.saveBeds24Selection(ids.length === allIds.length ? null : ids);
    },
    onSuccess: () => {
      setStep(4);
      importRemote.mutate();
      qc.invalidateQueries({ queryKey: ["connection"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (info.isLoading) return <Skeleton className="h-96" />;
  const c = info.data;
  if (!c) return null;

  const connected = c.mode !== "manual" && c.status === "connected" && c.has_token;
  const current: Step = step ?? (connected ? 4 : 1);
  const toggle = (id: string) =>
    setPicked((old) => {
      const n = new Set(old);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold">{t.title}</h1>
        <p className="text-sm text-muted-foreground">{t.intro}</p>
      </div>
      {c.sandbox && <p className="rounded-md bg-amber-500/10 p-2 text-xs text-amber-700">{t.sandbox}</p>}

      <ol className="flex flex-wrap gap-2 text-xs">
        {t.steps.map((label, i) => (
          <li key={label}
            className={cn("rounded-full border px-2 py-0.5", current === i + 1
              ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground")}>
            {i + 1}. {label}
          </li>
        ))}
      </ol>

      {connected && step === null && (
        <Card className="space-y-3">
          <div className="flex items-center gap-2">
            <CardTitle>{t.connected.title}</CardTitle>
            <Badge variant="success">{t.statuses.connected}</Badge>
          </div>
          {c.last_verified_at && (
            <CardDescription>{t.connected.since(dateTime(c.last_verified_at, lang))}</CardDescription>
          )}
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => loadRooms.mutate()} disabled={loadRooms.isPending}>{t.connected.change}</Button>
            <Button className="bg-muted text-foreground" onClick={() => { setStep(4); importRemote.mutate(); }}>
              {t.connected.reimport}
            </Button>
            <Button className="bg-muted text-foreground" onClick={() => setStep(1)}>{t.connected.reconnect}</Button>
          </div>
        </Card>
      )}

      {current === 1 && (!connected || step === 1) && (
        <Card className="space-y-3">
          <CardTitle>{t.step1.title}</CardTitle>
          <a href={BEDS24_URL} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
            {t.step1.open} <ExternalLink className="h-3.5 w-3.5" />
          </a>
          <p className="text-sm">{t.step1.path}</p>
          <p className="text-sm text-muted-foreground">{t.step1.perms}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <PermList title={t.step1.read} items={READ} copy={t.step1.copy} copied={t.step1.copied} />
            <PermList title={t.step1.write} items={WRITE} copy={t.step1.copy} copied={t.step1.copied} />
          </div>
          <p className="text-xs text-amber-700">{t.step1.expires}</p>
          <details className="rounded-md border border-border p-3 text-sm">
            <summary className="cursor-pointer font-medium">{t.guideTitle}</summary>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
              {t.guideItems.map((g) => <li key={g}>{g}</li>)}
            </ul>
            <div className="mt-2 flex flex-wrap gap-3 text-xs">
              <a href={GUIDE.airbnb} target="_blank" rel="noreferrer" className="text-primary hover:underline">{t.guideLinks.airbnb}</a>
              <a href={GUIDE.booking} target="_blank" rel="noreferrer" className="text-primary hover:underline">{t.guideLinks.booking}</a>
            </div>
          </details>
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => setStep(2)}>{t.step1.next}</Button>

          </div>
        </Card>
      )}

      {current === 2 && (
        <Card className="space-y-3">
          <CardTitle>{t.step2.title}</CardTitle>
          <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder={t.step2.placeholder}
            autoComplete="off" spellCheck={false} />
          <div className="flex gap-2">
            <Button onClick={() => redeem.mutate()} disabled={!code.trim() || redeem.isPending}>
              {redeem.isPending ? t.step2.validating : t.step2.validate}
            </Button>
            <Button className="bg-muted text-foreground" onClick={() => setStep(1)}>{t.step2.back}</Button>
          </div>
        </Card>
      )}

      {current === 3 && rooms && (
        <Card className="space-y-3">
          <CardTitle>{t.step3.title}</CardTitle>
          <CardDescription>{t.step3.hint}</CardDescription>
          <ul className="space-y-3">
            {rooms.properties.map((p) => (
              <li key={p.id} className={cn("rounded-md border border-border p-3", p.taken && "opacity-60")}>
                <p className="text-sm font-medium">
                  {p.name} <span className="text-xs font-normal text-muted-foreground">· {p.currency}</span>
                </p>
                {p.taken && <p className="text-xs text-amber-700">{t.step3.taken}</p>}
                <div className="mt-2 space-y-1">
                  {p.rooms.map((r) => (
                    <label key={r.id} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" disabled={p.taken} checked={!p.taken && picked.has(r.id)}
                        onChange={() => toggle(r.id)} />
                      <span>{r.name}</span>
                      <span className="text-xs text-muted-foreground">· {t.step3.units(r.units)}</span>
                    </label>
                  ))}
                </div>
              </li>
            ))}
          </ul>
          {(rooms.manual_units ?? []).length > 0 && (
            <div className="space-y-2 rounded-md border border-primary/40 p-3">
              <p className="text-sm font-medium">{t.link.title}</p>
              <p className="text-xs text-muted-foreground">{t.link.hint}</p>
              {(rooms.manual_units ?? []).map((u) => (
                <label key={u.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="min-w-32 font-medium">{u.name}</span>
                  <select className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                    value={links[u.id] ?? ""} onChange={(e) => setLinks((l) => ({ ...l, [u.id]: e.target.value }))}>
                    <option value="">{t.link.pick}</option>
                    {rooms.properties.filter((p) => !p.taken).flatMap((p) => p.rooms
                      .filter((r) => picked.has(r.id))
                      .map((r) => <option key={r.id} value={r.id}>{p.name} · {r.name}</option>))}
                  </select>
                </label>
              ))}
            </div>
          )}
          <Button onClick={() => save.mutate()} disabled={save.isPending || picked.size === 0}>{t.step3.save}</Button>
        </Card>
      )}

      {current === 4 && step === 4 && (
        <Card className="space-y-3">
          <CardTitle>{t.step4.title}</CardTitle>
          {importRemote.isPending && <p className="text-sm text-muted-foreground">{t.step4.running}</p>}
          {importRemote.data && <p className="text-sm">{t.step4.done(importRemote.data.created)}</p>}
          {importRemote.isError && <p className="text-sm text-red-600">{t.step4.failed}</p>}
          {!importRemote.isPending && (
            <Link href="/" className="inline-block"><Button>{t.step4.go}</Button></Link>
          )}
        </Card>
      )}
    </div>
  );
}

function PermList({ title, items, copy, copied }: { title: string; items: string[]; copy: string; copied: string }) {
  const [done, setDone] = useState(false);
  return (
    <div className="rounded-md border border-border p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-medium">{title}</span>
        <button type="button" className="inline-flex items-center gap-1 text-xs text-primary"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(items.join(", "));
              setDone(true);
              setTimeout(() => setDone(false), 1500);
            } catch {
              /* sin portapapeles: el texto está a la vista */
            }
          }}>
          {done ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />} {done ? copied : copy}
        </button>
      </div>
      <ul className="text-sm">
        {items.map((i) => <li key={i}><code>{i}</code></li>)}
      </ul>
    </div>
  );
}
