"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

// Panel del administrador de plataforma (feature 026, entrega 3). La API exige el rol: aquí
// solo se oculta la página a quien no lo tiene.
export default function AdminPage() {
  const { m } = useI18n();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  if (me.isLoading) return null;
  if (!me.data?.user.is_platform_admin) {
    return <p className="p-6 text-sm text-muted-foreground">{m.admin.notAllowed}</p>;
  }
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-xl font-semibold">{m.admin.title}</h1>
      <InvitesCard />
      <AccountsCard />
      <RegistrationCard />
    </div>
  );
}

async function copy(text: string, done: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(done);
  } catch {
    toast(text);
  }
}

function InvitesCard() {
  const { m, lang } = useI18n();
  const t = m.admin.invites;
  const qc = useQueryClient();
  const invites = useQuery({ queryKey: ["admin-invites"], queryFn: api.listInvites });
  const [note, setNote] = useState("");
  const [days, setDays] = useState("30");
  const [fresh, setFresh] = useState<string | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["admin-invites"] });

  const create = useMutation({
    mutationFn: () => api.createInvite(note.trim(), Number(days) || 30),
    onSuccess: (r) => {
      setFresh(r.code);
      setNote("");
      toast.success(t.created);
      refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const revoke = useMutation({
    mutationFn: (id: number) => api.revokeInvite(id),
    onSuccess: () => {
      toast(t.revoked);
      refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const link = fresh ? `${window.location.origin}/register?code=${fresh}` : "";

  return (
    <Card className="space-y-3">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.description}</CardDescription>
      <div className="flex flex-wrap gap-2">
        <Input className="min-w-0 flex-1" placeholder={t.note} value={note}
          onChange={(e) => setNote(e.target.value)} maxLength={200} />
        <Input className="w-24" inputMode="numeric" aria-label={t.days} title={t.days}
          value={days} onChange={(e) => setDays(e.target.value.replace(/\D/g, ""))} />
        <Button onClick={() => create.mutate()} disabled={create.isPending}>{t.create}</Button>
      </div>
      {fresh && (
        <div className="space-y-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3">
          <p className="font-mono text-lg tracking-wider">{fresh}</p>
          <div className="flex flex-wrap gap-2">
            <Button className="bg-muted text-foreground" onClick={() => copy(fresh, t.copied)}>
              <Copy size={14} className="mr-1" /> {t.copy}
            </Button>
            <Button className="bg-muted text-foreground" onClick={() => copy(link, t.copied)}>
              <Copy size={14} className="mr-1" /> {t.copyLink}
            </Button>
          </div>
        </div>
      )}
      {invites.data && invites.data.length === 0 && (
        <p className="text-sm text-muted-foreground">{t.empty}</p>
      )}
      <ul className="divide-y text-sm">
        {invites.data?.map((inv) => (
          <li key={inv.id} className="flex flex-wrap items-center gap-2 py-2">
            <span className="font-mono">SL-…{inv.last4}</span>
            <Badge variant={inv.status === "active" ? "success" : "default"}>
              {t.status[inv.status] ?? inv.status}
            </Badge>
            <span className="min-w-0 flex-1 truncate text-muted-foreground">
              {inv.note ?? ""}
              {inv.used_by_account ? ` · ${t.usedBy(inv.used_by_account.name)}` : ""}
              {inv.status === "active" ? ` · ${t.expires(dateTime(inv.expires_at, lang))}` : ""}
            </span>
            {inv.status === "active" && (
              <Button className="bg-muted text-foreground" onClick={() => revoke.mutate(inv.id)}
                disabled={revoke.isPending}>
                {t.revoke}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}

function AccountsCard() {
  const { m, lang } = useI18n();
  const t = m.admin.accounts;
  const qc = useQueryClient();
  const accounts = useQuery({ queryKey: ["admin-accounts"], queryFn: api.listAccounts });
  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      api.setAccountEnabled(id, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-accounts"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Card className="space-y-3">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.description}</CardDescription>
      <ul className="divide-y text-sm">
        {accounts.data?.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center gap-2 py-2">
            <div className="min-w-0 flex-1">
              <p className="font-medium">
                #{a.id} {a.name}{" "}
                {a.status === "disabled" && <Badge variant="warning">{t.disabled}</Badge>}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {t.owner}: {a.owner_email ?? "—"} · {a.connected ? t.connected : t.notConnected} ·{" "}
                {t.properties(a.properties)} ·{" "}
                {a.last_seen_at ? t.lastSeen(dateTime(a.last_seen_at, lang)) : t.never}
              </p>
            </div>
            {a.id !== 1 &&
              (a.status === "active" ? (
                <Button
                  className="bg-muted text-foreground"
                  onClick={() => {
                    if (window.confirm(t.confirmDisable(a.name))) {
                      toggle.mutate({ id: a.id, enabled: false });
                    }
                  }}
                  disabled={toggle.isPending}
                >
                  {t.disable}
                </Button>
              ) : (
                <Button onClick={() => toggle.mutate({ id: a.id, enabled: true })}
                  disabled={toggle.isPending}>
                  {t.enable}
                </Button>
              ))}
          </li>
        ))}
      </ul>
    </Card>
  );
}

function RegistrationCard() {
  const { m } = useI18n();
  const t = m.admin.registration;
  const qc = useQueryClient();
  const s = useQuery({ queryKey: ["admin-settings"], queryFn: api.adminSettings });
  const set = useMutation({
    mutationFn: (open: boolean) => api.setRegistrationOpen(open),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-settings"] }),
    onError: (e: Error) => toast.error(e.message),
  });
  const open = s.data?.registration_open ?? false;
  return (
    <Card className="space-y-2">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.description}</CardDescription>
      <div className="flex gap-2">
        <Button className={open ? "" : "bg-muted text-foreground"} onClick={() => set.mutate(true)}
          disabled={set.isPending || open}>
          {t.on}
        </Button>
        <Button className={!open ? "" : "bg-muted text-foreground"} onClick={() => set.mutate(false)}
          disabled={set.isPending || !open}>
          {t.off}
        </Button>
      </div>
    </Card>
  );
}
