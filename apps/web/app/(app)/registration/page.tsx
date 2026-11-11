"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Copy, ExternalLink, Link2, Send } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { toast } from "sonner";
import { GuestForm, checkinUrl, emptyGuests } from "@/components/registration/guest-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ApiError } from "@/lib/api";
import { dateTime, formatCOP, shortRange } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { GuestData, RegistrationSettings } from "@/lib/types";
import { cn } from "@/lib/utils";

// Registro de huéspedes: TRA del MinCIT (feature 046, #167). El anfitrión revisa y envía; nada sale solo.
const CHANNEL: Record<string, string> = { booking: "Booking.com", airbnb: "Airbnb", direct: "Directa" };
const TOKEN_URL = "https://pms.mincit.gov.co/token/";

export default function RegistrationPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96" />}>
      <RegistrationContent />
    </Suspense>
  );
}

function statusVariant(s: string | null): "success" | "warning" | "danger" | "muted" {
  if (s === "tra_sent") return "success";
  if (s === "tra_error" || s === "tra_partial") return "danger";
  if (s === "submitted") return "warning";
  return "muted";
}

function RegistrationContent() {
  const { m, lang } = useI18n();
  const t = m.registration;
  const router = useRouter();
  const selected = Number(useSearchParams().get("booking")) || null;
  const q = useQuery({ queryKey: ["registration"], queryFn: api.registrations });
  const open = (id: number | null) => router.replace(id ? `/registration?booking=${id}` : "/registration");

  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError) return <p className="text-sm text-red-600">{(q.error as Error).message}</p>;
  const data = q.data;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">{t.title}</h1>
        <p className="text-sm text-muted-foreground">{t.intro}</p>
      </div>
      <SetupCard s={data.settings} />
      <div className="grid gap-4 md:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <div className={cn("space-y-2", selected && "hidden md:block")}>
          {data.bookings.length === 0 && <p className="text-sm text-muted-foreground">{t.list.empty}</p>}
          {data.bookings.map((b) => (
            <button key={b.booking_id} type="button" onClick={() => open(b.booking_id)}
              className={cn("w-full rounded-md border p-3 text-left text-sm",
                b.booking_id === selected ? "border-primary bg-primary/5" : "border-border bg-card hover:bg-muted")}>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-medium">{b.guest_name || "—"}</span>
                <Badge variant={statusVariant(b.status)}>{t.statuses[b.status ?? "none"]}</Badge>
              </div>
              <p className="truncate text-xs text-muted-foreground">
                {CHANNEL[b.channel] ?? b.channel} · {b.unit ?? ""} · {shortRange(b.check_in, b.check_out, lang)}
              </p>
              {(b.guests || b.foreign) && (
                <p className="text-xs text-muted-foreground">
                  {b.guests ? t.list.guests(b.guests) : ""}{b.foreign ? ` · ${t.list.foreign}` : ""}
                </p>
              )}
            </button>
          ))}
        </div>
        <div className={cn(!selected && "hidden md:block")}>
          {selected ? <Detail bookingId={selected} onBack={() => open(null)} />
            : <Card><CardDescription>{t.detail.pick}</CardDescription></Card>}
        </div>
      </div>
    </div>
  );
}

function SetupCard({ s }: { s: RegistrationSettings }) {
  const { m } = useI18n();
  const t = m.registration.setup;
  const qc = useQueryClient();
  const [rnt, setRnt] = useState(s.rnt ?? "");
  const [name, setName] = useState(s.establishment_name ?? "");
  const [token, setToken] = useState("");
  const [authorize, setAuthorize] = useState(Boolean(s.authorized_at));
  const [open, setOpen] = useState(s.missing.length > 0);

  const save = useMutation({
    mutationFn: async () => {
      if (token.trim()) await api.setSecret("mincit_tra_token", token.trim());
      return api.saveRegistrationSettings({ rnt, establishment_name: name, authorize });
    },
    onSuccess: () => {
      setToken("");
      toast.success(t.saved);
      qc.invalidateQueries({ queryKey: ["registration"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Card className="space-y-3">
      <button type="button" className="flex w-full items-center justify-between text-left" onClick={() => setOpen((v) => !v)}>
        <CardTitle>{t.title}</CardTitle>
        <span className="text-xs text-muted-foreground">{open ? "▲" : "▼"}</span>
      </button>
      {s.sandbox && <p className="rounded-md bg-amber-500/10 p-2 text-xs text-amber-700">{t.sandbox}</p>}
      {s.missing.length > 0 && (
        <p className="text-xs text-amber-700">{t.missing} {s.missing.map((k) => t.missingItems[k] ?? k).join(", ")}.</p>
      )}
      {open && (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block space-y-1 text-xs">
              <span className="font-medium">{t.rnt}</span>
              <Input value={rnt} onChange={(e) => setRnt(e.target.value)} inputMode="numeric" maxLength={20} />
            </label>
            <label className="block space-y-1 text-xs">
              <span className="font-medium">{t.name}</span>
              <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
            </label>
          </div>
          <label className="block space-y-1 text-xs">
            <span className="flex items-center gap-2 font-medium">
              {t.token}
              <Badge variant={s.has_token ? "success" : "muted"}>{s.has_token ? t.tokenSet : t.tokenMissing}</Badge>
            </span>
            <Input type="password" value={token} onChange={(e) => setToken(e.target.value)} autoComplete="off"
              spellCheck={false} maxLength={200} />
            <span className="flex flex-wrap items-center gap-2 text-muted-foreground">
              {t.tokenHelp}
              <a href={TOKEN_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary">
                {t.openToken} <ExternalLink className="h-3 w-3" />
              </a>
            </span>
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1" checked={authorize} onChange={(e) => setAuthorize(e.target.checked)} />
            <span>{t.authorize}</span>
          </label>
          <Button onClick={() => save.mutate()} disabled={save.isPending}>{t.save}</Button>
        </div>
      )}
    </Card>
  );
}

function Detail({ bookingId, onBack }: { bookingId: number; onBack: () => void }) {
  const { m, lang } = useI18n();
  const t = m.registration;
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["registration", bookingId], queryFn: () => api.registration(bookingId) });
  const [data, setData] = useState<GuestData>(emptyGuests);
  const [cost, setCost] = useState("");
  const [errors, setErrors] = useState<Record<string, string[]> | undefined>();
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    if (!q.data) return;
    setData(q.data.data ?? emptyGuests());
    setCost(q.data.cost_cop ?? q.data.cost_proposed ?? "");
    setErrors(undefined);
    setEditing(false);
  }, [q.data]);

  const refresh = (d: unknown) => {
    qc.setQueryData(["registration", bookingId], d);
    qc.invalidateQueries({ queryKey: ["registration"], exact: true });
  };
  const link = useMutation({
    mutationFn: () => api.registrationLink(bookingId),
    onSuccess: async (r) => {
      await copy(checkinUrl(r.token));
      qc.invalidateQueries({ queryKey: ["registration"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const save = useMutation({
    mutationFn: () => api.saveRegistration(bookingId, data, cost.replace(/\D/g, "") || null),
    onSuccess: (d) => { refresh(d); toast.success(t.detail.saved); },
    onError: (e: ApiError) => { setErrors(e.fields); toast.error(e.message); },
  });
  const send = useMutation({
    mutationFn: () => api.sendTra(bookingId),
    onSuccess: (d) => {
      refresh(d);
      if (d.status === "tra_sent") toast.success(t.detail.sent);
      else toast.error(d.tra_error ?? t.statuses[d.status ?? "tra_error"]);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  async function copy(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      toast.success(t.link.copied);
    } catch {
      window.prompt(t.link.copy, url);
    }
  }

  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError) return <p className="text-sm text-red-600">{(q.error as Error).message}</p>;
  const d = q.data;
  if (!d) return null;
  const hasData = Boolean(d.data);

  return (
    <Card className="space-y-4">
      <div className="flex items-start gap-2">
        <button type="button" onClick={onBack} className="mt-0.5 md:hidden" aria-label={t.detail.back}>
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="truncate">{d.guest_name || "—"}</CardTitle>
            <Badge variant={statusVariant(d.status)}>{t.statuses[d.status ?? "none"]}</Badge>
          </div>
          <CardDescription>
            {CHANNEL[d.channel] ?? d.channel} · {d.unit ?? ""} · {shortRange(d.check_in, d.check_out, lang)}
            {d.filled_by ? ` · ${d.filled_by === "guest" ? t.byGuest : t.byHost}` : ""}
          </CardDescription>
        </div>
      </div>

      {d.editable && (
        <div className="flex flex-wrap gap-2">
          {d.token ? (
            <Button className="bg-muted text-foreground" onClick={() => copy(checkinUrl(d.token!))}>
              <Copy className="mr-1 h-4 w-4" /> {t.link.copy}
            </Button>
          ) : (
            <Button className="bg-muted text-foreground" onClick={() => link.mutate()} disabled={link.isPending}>
              <Link2 className="mr-1 h-4 w-4" /> {t.link.create}
            </Button>
          )}
          {hasData && !editing && (
            <Button className="bg-muted text-foreground" onClick={() => setEditing(true)}>{t.detail.edit}</Button>
          )}
        </div>
      )}

      {d.tra_sent_at && (
        <div className="space-y-1 rounded-md border border-border p-3 text-sm">
          <p>{t.detail.sentAt(dateTime(d.tra_sent_at, lang))}</p>
          {d.tra_code != null && <p className="text-xs text-muted-foreground">{t.detail.code(d.tra_code)}</p>}
          <p className="text-xs text-muted-foreground">{t.detail.locked}</p>
        </div>
      )}
      {d.tra_error && <p className="rounded-md bg-red-500/10 p-2 text-sm text-red-700 dark:text-red-400">{d.tra_error}</p>}

      {!hasData && !editing && d.editable && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{t.detail.noData}</p>
          <Button className="bg-muted text-foreground" onClick={() => setEditing(true)}>{t.detail.edit}</Button>
        </div>
      )}

      {(hasData || editing) && (
        <GuestForm value={data} onChange={setData} errors={errors} disabled={!editing || !d.editable} />
      )}

      {d.editable && (hasData || editing) && (
        <label className="block space-y-1 text-xs">
          <span className="font-medium">{t.detail.cost}</span>
          <Input value={cost ? formatCOP(cost, lang) : ""} inputMode="numeric"
            onChange={(e) => setCost(e.target.value.replace(/\D/g, ""))} />
          <span className="text-muted-foreground">{t.detail.costHelp}</span>
        </label>
      )}

      {d.editable && (
        <div className="flex flex-wrap gap-2">
          {(editing || cost !== (d.cost_cop ?? d.cost_proposed ?? "")) && (
            <Button onClick={() => save.mutate()} disabled={save.isPending}>{t.detail.save}</Button>
          )}
          {hasData && !editing && (
            <Button onClick={() => { if (window.confirm(t.detail.confirm)) send.mutate(); }} disabled={send.isPending}>
              <Send className="mr-1 h-4 w-4" /> {send.isPending ? t.detail.sending : t.detail.send}
            </Button>
          )}
        </div>
      )}
      {!d.editable && d.status === "tra_partial" && (
        <Button onClick={() => send.mutate()} disabled={send.isPending}>
          <Send className="mr-1 h-4 w-4" /> {send.isPending ? t.detail.sending : t.detail.send}
        </Button>
      )}
    </Card>
  );
}
