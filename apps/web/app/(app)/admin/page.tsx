"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { BetaCard } from "@/components/admin/beta-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import type { AdminUsageRow } from "@/lib/types";
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
      <UsageAdminCard />
      <BetaCard />
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
                {a.status === "deleted" && <Badge>{m.legal.adminDeleted}</Badge>}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {t.owner}: {a.owner_email ?? "—"} · {a.connected ? t.connected : t.notConnected} ·{" "}
                {t.properties(a.properties)} ·{" "}
                {a.last_seen_at ? t.lastSeen(dateTime(a.last_seen_at, lang)) : t.never}
              </p>
            </div>
            {a.id !== 1 && a.status !== "deleted" &&
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

function LimitsEditor({ row }: { row: AdminUsageRow }) {
  const { m } = useI18n();
  const t = m.usage.admin;
  const qc = useQueryClient();
  const [chat, setChat] = useState(String(row.chat_limit_month));
  const [search, setSearch] = useState(String(row.search_limit_day));
  const save = useMutation({
    mutationFn: (body: { chat_limit_month: number | null; search_limit_day: number | null }) =>
      api.setAccountLimits(row.id, body),
    onSuccess: () => {
      toast.success(t.saved);
      qc.invalidateQueries({ queryKey: ["admin-usage"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <div className="flex flex-wrap items-center gap-1">
      <Input className="h-8 w-20" inputMode="numeric" value={chat}
        onChange={(e) => setChat(e.target.value.replace(/\D/g, ""))} />
      <Input className="h-8 w-16" inputMode="numeric" value={search}
        onChange={(e) => setSearch(e.target.value.replace(/\D/g, ""))} />
      <Button className="h-8 px-2 text-xs" disabled={save.isPending || !chat || !search}
        onClick={() => save.mutate({ chat_limit_month: Number(chat), search_limit_day: Number(search) })}>
        {t.save}
      </Button>
      {row.custom_limits && (
        <Button className="h-8 bg-muted px-2 text-xs text-foreground" disabled={save.isPending}
          onClick={() => save.mutate({ chat_limit_month: null, search_limit_day: null })}>
          {t.reset}
        </Button>
      )}
    </div>
  );
}

function UsageAdminCard() {
  const { m } = useI18n();
  const t = m.usage.admin;
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const usage = useQuery({ queryKey: ["admin-usage", month], queryFn: () => api.adminUsage(month) });
  const rows = usage.data?.accounts ?? [];
  const unpriced = rows.reduce((n, r) => n + r.unpriced, 0);
  return (
    <Card className="space-y-3">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.description}</CardDescription>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <label className="flex items-center gap-2">
          {t.month}
          <Input type="month" className="h-8 w-40" value={month}
            onChange={(e) => e.target.value && setMonth(e.target.value)} />
        </label>
        {usage.data && (
          <span className="font-medium">{t.total(usage.data.total_cost_usd.toFixed(2))}</span>
        )}
      </div>
      {unpriced > 0 && <p className="text-xs text-amber-600">{t.unpriced(unpriced)}</p>}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-muted-foreground">
            <tr>
              <th className="py-1 pr-2">#</th>
              <th className="py-1 pr-2">{t.messages}</th>
              <th className="py-1 pr-2">{t.calls}</th>
              <th className="py-1 pr-2">{t.tokens}</th>
              <th className="py-1 pr-2">{t.searches}</th>
              <th className="py-1 pr-2">{t.cost}</th>
              <th className="py-1">{t.limits}</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="py-2 pr-2">
                  #{r.id} {r.name || "—"}
                </td>
                <td className="py-2 pr-2">{r.chat_messages}/{r.chat_limit_month}</td>
                <td className="py-2 pr-2">{r.llm_calls}</td>
                <td className="py-2 pr-2">{(r.input_tokens + r.output_tokens).toLocaleString()}</td>
                <td className="py-2 pr-2">{r.searches}</td>
                <td className="py-2 pr-2">{r.cost_usd.toFixed(4)}</td>
                <td className="py-2">
                  {r.status === "deleted" ? "—" : <LimitsEditor key={`${r.id}-${r.chat_limit_month}-${r.search_limit_day}`} row={r} />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p className="text-sm text-muted-foreground">{t.empty}</p>}
    </Card>
  );
}
