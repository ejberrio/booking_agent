"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useActiveUnit } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { dateTime, formatNumber } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Messages } from "@/lib/i18n/messages";
import { trServer } from "@/lib/i18n/server-messages";
import type { OffsetPreview, Poi, SecretStatus, SecretTestResult, WebhookStatus } from "@/lib/types";

const CHANNEL_NAMES: Record<string, string> = { booking: "Booking.com", airbnb: "Airbnb" };
const cop = (v: string) => `${formatNumber(Number(v))} COP`;

/** Avisos de la vista previa del ajuste por canal: el conocido se traduce aquí; el resto, vía trServer. */
function offsetWarning(w: string, t: Messages["settings"]["offsets"]): string {
  const inactive = /^el canal (\w+) está inactivo: /.exec(w);
  if (inactive) return t.inactiveWarning(CHANNEL_NAMES[inactive[1]] ?? inactive[1]);
  return trServer(w);
}

function ChannelOffsetsCard() {
  const { m } = useI18n();
  const t = m.settings.offsets;
  const qc = useQueryClient();
  const offsets = useQuery({
    queryKey: ["channel-offsets"],
    queryFn: () => api.getChannelOffsets(),
  });
  const [editing, setEditing] = useState<string | null>(null);
  const [pct, setPct] = useState("");
  const [preview, setPreview] = useState<OffsetPreview | null>(null);

  const previewM = useMutation({
    mutationFn: () =>
      api.previewChannelOffset({ channel: editing!, offset_pct: Number(pct) }),
    onSuccess: setPreview,
    onError: (e: Error) => toast.error(e.message),
  });
  const applyM = useMutation({
    mutationFn: () =>
      api.applyChannelOffset({
        channel: editing!,
        offset_pct: Number(pct),
        fingerprint: preview!.fingerprint,
      }),
    onSuccess: (r) => {
      if (r.verified)
        toast.success(t.applied(CHANNEL_NAMES[r.channel] ?? r.channel, String(r.offset_pct)));
      else toast.warning(t.appliedUnverified(r.issue ? trServer(r.issue) : t.checkIssues));
      setEditing(null);
      setPreview(null);
      setPct("");
      qc.invalidateQueries({ queryKey: ["channel-offsets"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Card className="space-y-2">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.description}</CardDescription>
      {offsets.isLoading ? (
        <Skeleton className="h-16 w-full" />
      ) : (
        <ul className="space-y-2 text-sm">
          {(offsets.data?.offsets ?? []).map((o) => (
            <li key={o.channel} className="rounded-md border border-border p-2">
              <div className="flex items-center justify-between">
                <span>
                  {CHANNEL_NAMES[o.channel] ?? o.channel}
                  {!o.is_active && (
                    <span className="ml-2 text-xs text-muted-foreground">{t.inactive}</span>
                  )}
                </span>
                <span className="flex items-center gap-2">
                  <Badge variant={o.offset_pct ? "warning" : "success"}>
                    {o.offset_pct ? `${o.offset_pct > 0 ? "+" : ""}${o.offset_pct}%` : "0%"}
                  </Badge>
                  {o.supported ? (
                    <Button
                      className="h-7 px-2 text-xs"
                      onClick={() => {
                        setEditing(o.channel);
                        setPct(String(o.offset_pct ?? 0));
                        setPreview(null);
                      }}
                    >
                      {m.common.edit}
                    </Button>
                  ) : (
                    <span
                      className="text-xs text-muted-foreground"
                      title={t.basePriceHint}
                    >
                      {t.basePrice}
                    </span>
                  )}
                </span>
              </div>
              {editing === o.channel && (
                <div className="mt-2 space-y-2 border-t border-border pt-2">
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      className="w-24"
                      value={pct}
                      onChange={(e) => setPct(e.target.value)}
                    />
                    <span className="text-xs text-muted-foreground">
                      {t.range}
                    </span>
                    <Button
                      className="h-7 px-2 text-xs"
                      onClick={() => previewM.mutate()}
                      disabled={previewM.isPending || pct === ""}
                    >
                      {t.preview}
                    </Button>
                  </div>
                  {preview && (
                    <div className="rounded-md bg-muted p-2 text-xs">
                      <p>
                        {preview.current_pct ?? "0"}% → <strong>{preview.new_pct}%</strong> · {t.example}{" "}
                        {t.base} {cop(preview.example.base)} →{" "}
                        <strong>{cop(preview.example.effective)}</strong>
                      </p>
                      {preview.warnings.map((w) => (
                        <p key={w} className="mt-1 text-amber-600">
                          ⚠️ {offsetWarning(w, t)}
                        </p>
                      ))}
                      <div className="mt-2 flex gap-2">
                        <Button
                          className="h-7 px-2 text-xs"
                          onClick={() => applyM.mutate()}
                          disabled={applyM.isPending}
                        >
                          {t.apply}
                        </Button>
                        <Button
                          className="h-7 bg-transparent px-2 text-xs text-muted-foreground hover:bg-muted"
                          onClick={() => {
                            setEditing(null);
                            setPreview(null);
                          }}
                        >
                          {m.common.cancel}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function sourceLabel(s: SecretStatus, t: Messages["settings"]["secrets"]): string {
  if (s.unreadable) return t.sourceUnreadable;
  if (s.source === "app") return `${t.sourceApp}${s.updated_at ? ` · ${s.updated_at.slice(0, 10)}` : ""}`;
  if (s.source === "env") return t.sourceEnv;
  return t.notConfigured;
}

/** Gestión write-only de secretos (feature 017): el valor nunca se muestra ni
 *  se puede recuperar; solo estado + pista de los últimos 4 caracteres. */
function SecretsCard() {
  const { m } = useI18n();
  const t = m.settings.secrets;
  // Guías, nombres y servicios por secreto (los desconocidos caen al texto del servidor).
  const help: Record<string, string | undefined> = t.help;
  const labels: Record<string, string | undefined> = t.labels;
  const services: Record<string, string | undefined> = t.services;
  const qc = useQueryClient();
  const secrets = useQuery({ queryKey: ["secrets"], queryFn: () => api.listSecrets() });
  const audit = useQuery({ queryKey: ["secrets-audit"], queryFn: () => api.listSecretAudit() });
  const [values, setValues] = useState<Record<string, string>>({});
  const [testResults, setTestResults] = useState<Record<string, SecretTestResult>>({});

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["secrets"] });
    qc.invalidateQueries({ queryKey: ["secrets-audit"] });
  };
  const onError = (e: Error) => toast.error(e.message);

  const save = useMutation({
    mutationFn: (name: string) => api.setSecret(name, values[name] ?? ""),
    onSuccess: (_r, name) => {
      toast.success(t.saved);
      setValues((v) => ({ ...v, [name]: "" })); // write-only: el campo se limpia
      refresh();
    },
    onError,
  });
  const remove = useMutation({
    mutationFn: (name: string) => api.deleteSecret(name),
    onSuccess: () => {
      toast(t.removed);
      refresh();
    },
    onError,
  });
  // Beds24: el host pega el código de invitación y el servidor lo canjea por el
  // refresh token (que nunca llega al navegador).
  const [inviteCode, setInviteCode] = useState("");
  const redeem = useMutation({
    mutationFn: () => api.redeemBeds24Invite(inviteCode),
    onSuccess: () => {
      toast.success(t.redeemed);
      setInviteCode("");
      setTestResults((prev) => ({
        ...prev,
        beds24_refresh_token: { ok: true, detail: t.newTokenSaved },
      }));
      refresh();
    },
    onError,
  });
  const test = useMutation({
    mutationFn: (name: string) => api.testSecret(name),
    onSuccess: (r, name) => setTestResults((prev) => ({ ...prev, [name]: r })),
    onError,
  });

  return (
    <Card className="space-y-3">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.description}</CardDescription>

      {secrets.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="space-y-3">
          {(secrets.data?.secrets ?? []).map((s) => (
            <div key={s.name} className="space-y-1.5 rounded-md border border-border p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{labels[s.name] ?? s.label}</span>
                <Badge variant={s.configured ? "success" : "warning"}>
                  {s.configured ? t.configured(s.hint) : t.notConfigured}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                {services[s.name] ?? s.service} · {sourceLabel(s, t)}
              </p>
              <div className="flex gap-2">
                <Input
                  type="password"
                  autoComplete="off"
                  placeholder={t.newValuePlaceholder}
                  value={values[s.name] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [s.name]: e.target.value }))}
                />
                <Button
                  onClick={() => save.mutate(s.name)}
                  disabled={save.isPending || !(values[s.name] ?? "").trim()}
                >
                  {m.common.save}
                </Button>
              </div>
              {help[s.name] && (
                <p className="text-[11px] text-muted-foreground">{help[s.name]}</p>
              )}
              {s.name === "beds24_refresh_token" && (
                <div className="space-y-1">
                  <div className="flex gap-2">
                    <Input
                      type="password"
                      autoComplete="off"
                      placeholder={t.invitePlaceholder}
                      value={inviteCode}
                      onChange={(e) => setInviteCode(e.target.value)}
                    />
                    <Button
                      onClick={() => redeem.mutate()}
                      disabled={redeem.isPending || !inviteCode.trim()}
                    >
                      {t.redeem}
                    </Button>
                  </div>
                  <p className="text-[11px] text-muted-foreground">{t.inviteHelp}</p>
                </div>
              )}
              <div className="flex items-center gap-2">
                <Button
                  className="bg-muted text-foreground"
                  onClick={() => test.mutate(s.name)}
                  disabled={test.isPending}
                >
                  {t.test}
                </Button>
                {s.source === "app" && (
                  <Button
                    className="bg-transparent text-muted-foreground hover:bg-muted"
                    onClick={() => remove.mutate(s.name)}
                    disabled={remove.isPending}
                  >
                    {t.remove}
                  </Button>
                )}
                {testResults[s.name] && (
                  <span
                    className={`text-xs ${testResults[s.name].ok ? "text-emerald-500" : "text-red-500"}`}
                  >
                    {testResults[s.name].ok ? "✓" : "✗"} {trServer(testResults[s.name].detail)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {(audit.data?.entries.length ?? 0) > 0 && (
        <div>
          <p className="text-xs font-medium">{t.recentChanges}</p>
          <ul className="mt-1 space-y-0.5 text-[11px] text-muted-foreground">
            {audit.data!.entries.slice(0, 6).map((e, i) => (
              <li key={i}>
                {e.changed_at.slice(0, 16).replace("T", " ")} · {labels[e.name] ?? e.name} ·{" "}
                {e.action === "set" ? t.auditSet(e.hint) : t.auditDeleted}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

/** POIs que dirigen las búsquedas del scan (feature 018). Dato local. */
function PoisCard() {
  const { m } = useI18n();
  const t = m.settings.pois;
  const qc = useQueryClient();
  const pois = useQuery({ queryKey: ["pois"], queryFn: () => api.listPois() });
  const empty = { name: "", note: "", from: "", to: "" };
  const [form, setForm] = useState(empty);

  const refresh = () => qc.invalidateQueries({ queryKey: ["pois"] });
  const onError = (e: Error) => toast.error(e.message);

  const create = useMutation({
    mutationFn: () =>
      api.createPoi({
        name: form.name.trim(),
        note: form.note.trim() || null,
        date_from: form.from || null,
        date_to: form.to || null,
      }),
    onSuccess: () => {
      toast.success(t.added);
      setForm(empty);
      refresh();
    },
    onError,
  });
  const toggle = useMutation({
    mutationFn: (p: Poi) => api.updatePoi(p.id, { is_active: !p.is_active }),
    onSuccess: refresh,
    onError,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deletePoi(id),
    onSuccess: refresh,
    onError,
  });

  const vigencia = (p: Poi) =>
    !p.date_from && !p.date_to
      ? t.always
      : `${p.date_from ?? "…"} → ${p.date_to ?? "…"}`;

  return (
    <Card className="space-y-3">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.description}</CardDescription>
      {pois.isLoading ? (
        <Skeleton className="h-16 w-full" />
      ) : (
        <div className="space-y-2">
          {(pois.data?.pois ?? []).map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between rounded-md border border-border p-2 text-sm"
            >
              <div className={p.is_active ? "" : "opacity-50"}>
                <span className="font-medium">{p.name}</span>
                <span className="text-xs text-muted-foreground">
                  {" "}
                  · {vigencia(p)}
                  {p.note ? ` · ${p.note}` : ""}
                  {p.is_active ? "" : ` · ${t.inactive}`}
                </span>
              </div>
              <div className="flex gap-1">
                <Button
                  className="bg-transparent px-2 text-muted-foreground hover:bg-muted"
                  onClick={() => toggle.mutate(p)}
                >
                  {p.is_active ? t.deactivate : t.reactivate}
                </Button>
                <Button
                  className="bg-transparent px-2 text-muted-foreground hover:bg-muted"
                  onClick={() => remove.mutate(p.id)}
                >
                  {t.remove}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="grid grid-cols-2 gap-2">
        <Input
          placeholder={t.namePlaceholder}
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
        <Input
          placeholder={t.notePlaceholder}
          value={form.note}
          onChange={(e) => setForm({ ...form, note: e.target.value })}
        />
        <Input type="date" aria-label={t.fromLabel} value={form.from} onChange={(e) => setForm({ ...form, from: e.target.value })} />
        <Input type="date" aria-label={t.toLabel} value={form.to} onChange={(e) => setForm({ ...form, to: e.target.value })} />
      </div>
      <Button onClick={() => create.mutate()} disabled={create.isPending || !form.name.trim()}>
        {t.add}
      </Button>
    </Card>
  );
}

/** Configuración del escaneo diario (feature 018). */
function ScanConfigCard() {
  const { m } = useI18n();
  const t = m.settings.scan;
  const qc = useQueryClient();
  const cfg = useQuery({ queryKey: ["scan-config"], queryFn: () => api.getScanConfig() });
  const [zone, setZone] = useState<string | null>(null);
  const [queries, setQueries] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () =>
      api.updateScanConfig({
        ...(zone !== null ? { zone: zone.trim() || null } : {}),
        ...(queries !== null ? { queries_per_scan: Number(queries) } : {}),
      }),
    onSuccess: () => {
      toast.success(t.saved);
      setZone(null);
      setQueries(null);
      qc.invalidateQueries({ queryKey: ["scan-config"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Card className="space-y-2">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>
        {t.effectiveZone} <strong>{cfg.data?.effective_zone ?? "…"}</strong> · {t.queriesPerRun}{" "}
        <strong>{cfg.data?.queries_per_scan ?? "…"}</strong> {t.freeQuota}
      </CardDescription>
      <div className="grid grid-cols-2 gap-2">
        <Input
          placeholder={t.zonePlaceholder}
          value={zone ?? cfg.data?.zone ?? ""}
          onChange={(e) => setZone(e.target.value)}
        />
        <Input
          type="number"
          placeholder={t.queriesPlaceholder}
          value={queries ?? String(cfg.data?.queries_per_scan ?? "")}
          onChange={(e) => setQueries(e.target.value)}
        />
      </div>
      <Button onClick={() => save.mutate()} disabled={save.isPending || (zone === null && queries === null)}>
        {m.common.save}
      </Button>
    </Card>
  );
}

const WEBHOOK_VARIANT: Record<WebhookStatus["status"], "success" | "warning" | "muted"> = {
  unconfigured: "muted",
  never: "warning",
  active: "success",
  idle: "warning",
};

function CopyRow({ value, secret }: { value: string; secret?: boolean }) {
  const { m } = useI18n();
  return (
    <div className="flex items-center gap-2">
      <code className="min-w-0 flex-1 truncate rounded bg-muted px-2 py-1 text-xs">
        {value}
      </code>
      <Button
        className="h-7 bg-muted px-2 text-xs text-foreground"
        onClick={() =>
          navigator.clipboard
            .writeText(value)
            .then(() => toast.success(secret ? m.settings.webhooks.lineCopied : m.common.copied))
            .catch(() => toast.error(m.common.copyFailed))
        }
      >
        {m.common.copy}
      </Button>
    </div>
  );
}

/** Reservas en tiempo real (feature 020): estado de los avisos de Beds24, clave y guía. */
function WebhooksCard() {
  const { m } = useI18n();
  const t = m.settings.webhooks;
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["webhook-status"],
    queryFn: () => api.getWebhookStatus(),
    refetchInterval: 60_000,
  });
  // La línea con la clave solo vive en memoria de esta pantalla: no se vuelve a mostrar.
  const [line, setLine] = useState<string | null>(null);
  const generate = useMutation({
    mutationFn: () => api.generateWebhookKey(),
    onSuccess: (r) => {
      setLine(r.header_line);
      qc.invalidateQueries({ queryKey: ["webhook-status"] });
      qc.invalidateQueries({ queryKey: ["secrets"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const st = status.data;
  const state = st ? { label: t.states[st.status], variant: WEBHOOK_VARIANT[st.status] } : null;

  const onGenerate = () => {
    if (
      st?.configured &&
      !window.confirm(t.confirmRegenerate)
    ) {
      return;
    }
    generate.mutate();
  };

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <CardTitle>{t.title}</CardTitle>
        {state && <Badge variant={state.variant}>{state.label}</Badge>}
      </div>
      <CardDescription>{t.description}</CardDescription>

      {status.isLoading ? (
        <Skeleton className="h-16 w-full" />
      ) : st ? (
        <>
          {st.configured && (
            <p className="text-xs text-muted-foreground">
              {t.lastNotice}{" "}
              {st.last_accepted_at ? dateTime(st.last_accepted_at) : t.noneYet} ·{" "}
              {t.stats(st.counts_7d.accepted, st.counts_7d.rejected, st.counts_7d.failed)}
            </p>
          )}

          {line ? (
            <div className="space-y-1.5 rounded-md border border-amber-500/40 p-2">
              <p className="text-xs font-medium">{t.copyNow}</p>
              <CopyRow value={line} secret />
            </div>
          ) : (
            <Button onClick={onGenerate} disabled={generate.isPending}>
              {st.configured ? t.generateNew : t.generate}
            </Button>
          )}

          <ol className="list-decimal space-y-1.5 pl-5 text-xs text-muted-foreground">
            <li>{t.step1}</li>
            <li>
              {t.step2Open} <strong>Settings → Properties → Access</strong>{t.step2Section}{" "}
              <strong>Booking Webhook</strong>.
            </li>
            <li>
              <strong>Webhook Version</strong>: 2.
            </li>
            <li>
              <strong>URL</strong>:
              <CopyRow value={st.endpoint_url} />
            </li>
            <li>
              <strong>Custom Header</strong>
              {t.step5Paste} <code>{st.header_name}:</code>
              {t.step5Press} <strong>Save</strong>.
            </li>
            <li>{t.step6(t.states.active)}</li>
          </ol>
        </>
      ) : (
        <p className="text-sm text-red-500">{t.loadError}</p>
      )}
    </Card>
  );
}

export default function SettingsPage() {
  const { m } = useI18n();
  const t = m.settings;
  const [unitTypeId] = useActiveUnit();
  const test = useMutation({ mutationFn: () => api.testConnection() });

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-xl font-semibold">{t.title}</h1>

      <Card className="space-y-2">
        <CardTitle>{t.beds24.title}</CardTitle>
        <CardDescription>{t.beds24.description}</CardDescription>
        <div className="flex items-center gap-2">
          <Button onClick={() => test.mutate()} disabled={test.isPending}>
            {t.beds24.check}
          </Button>
          {test.data && (
            <Badge variant={test.data.status === "connected" ? "success" : "warning"}>
              {t.beds24.status[test.data.status] ?? test.data.status}
            </Badge>
          )}
        </div>
      </Card>

      <WebhooksCard />

      <ChannelOffsetsCard />

      <PoisCard />

      <ScanConfigCard />

      <SecretsCard />

      <Card className="space-y-1">
        <CardTitle>{t.llm.title}</CardTitle>
        <CardDescription>{t.llm.description}</CardDescription>
      </Card>

      <Card className="space-y-1">
        <CardTitle>{t.prefs.title}</CardTitle>
        <CardDescription>{t.prefs.activeUnit(unitTypeId)}</CardDescription>
      </Card>
    </div>
  );
}
