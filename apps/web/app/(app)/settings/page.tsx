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
import type { OffsetPreview, SecretStatus, SecretTestResult } from "@/lib/types";

const CHANNEL_NAMES: Record<string, string> = { booking: "Booking.com", airbnb: "Airbnb" };
const cop = (v: string) => `${Number(v).toLocaleString("es-CO")} COP`;

function ChannelOffsetsCard() {
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
        toast.success(
          `Ajuste de ${CHANNEL_NAMES[r.channel] ?? r.channel} aplicado: ${r.offset_pct}%`,
        );
      else toast.warning(`Aplicado, pero sin verificar: ${r.issue ?? "revisa incidencias"}`);
      setEditing(null);
      setPreview(null);
      setPct("");
      qc.invalidateQueries({ queryKey: ["channel-offsets"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Card className="space-y-2">
      <CardTitle>Precio por canal</CardTitle>
      <CardDescription>
        Recargo/descuento porcentual por canal sobre el precio base (0% = mismo precio).
        Airbnb muestra el importe en la moneda del huésped (su margen cambiario no depende de
        nosotros).
      </CardDescription>
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
                    <span className="ml-2 text-xs text-muted-foreground">(inactivo)</span>
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
                      Editar
                    </Button>
                  ) : (
                    <span
                      className="text-xs text-muted-foreground"
                      title="Este canal vende al precio base; su ajuste no es configurable"
                    >
                      precio base
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
                      % (−50 a 100; 0 = quitar)
                    </span>
                    <Button
                      className="h-7 px-2 text-xs"
                      onClick={() => previewM.mutate()}
                      disabled={previewM.isPending || pct === ""}
                    >
                      Ver propuesta
                    </Button>
                  </div>
                  {preview && (
                    <div className="rounded-md bg-muted p-2 text-xs">
                      <p>
                        {preview.current_pct ?? "0"}% → <strong>{preview.new_pct}%</strong> · ej.:
                        base {cop(preview.example.base)} →{" "}
                        <strong>{cop(preview.example.effective)}</strong>
                      </p>
                      {preview.warnings.map((w) => (
                        <p key={w} className="mt-1 text-amber-600">
                          ⚠️ {w}
                        </p>
                      ))}
                      <div className="mt-2 flex gap-2">
                        <Button
                          className="h-7 px-2 text-xs"
                          onClick={() => applyM.mutate()}
                          disabled={applyM.isPending}
                        >
                          Confirmar y aplicar
                        </Button>
                        <Button
                          className="h-7 bg-transparent px-2 text-xs text-muted-foreground hover:bg-muted"
                          onClick={() => {
                            setEditing(null);
                            setPreview(null);
                          }}
                        >
                          Cancelar
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

function sourceLabel(s: SecretStatus): string {
  if (s.unreadable) return "guardado ilegible — se usa la variable de entorno";
  if (s.source === "app") return `guardado en la app${s.updated_at ? ` · ${s.updated_at.slice(0, 10)}` : ""}`;
  if (s.source === "env") return "por variable de entorno";
  return "sin configurar";
}

/** Gestión write-only de secretos (feature 017): el valor nunca se muestra ni
 *  se puede recuperar; solo estado + pista de los últimos 4 caracteres. */
function SecretsCard() {
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
      toast.success("Secreto guardado — la rotación ya aplica");
      setValues((v) => ({ ...v, [name]: "" })); // write-only: el campo se limpia
      refresh();
    },
    onError,
  });
  const remove = useMutation({
    mutationFn: (name: string) => api.deleteSecret(name),
    onSuccess: () => {
      toast("Valor guardado eliminado (se usa la variable de entorno si existe)");
      refresh();
    },
    onError,
  });
  const test = useMutation({
    mutationFn: (name: string) => api.testSecret(name),
    onSuccess: (r, name) => setTestResults((t) => ({ ...t, [name]: r })),
    onError,
  });

  return (
    <Card className="space-y-3">
      <CardTitle>Secretos</CardTitle>
      <CardDescription>
        API keys y tokens de los servicios. Write-only: el valor nunca se muestra; pega uno
        nuevo para rotarlo. La rotación aplica de inmediato en la API; el escaneo diario la
        toma en su próxima corrida.
      </CardDescription>

      {secrets.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="space-y-3">
          {(secrets.data?.secrets ?? []).map((s) => (
            <div key={s.name} className="space-y-1.5 rounded-md border border-border p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{s.label}</span>
                <Badge variant={s.configured ? "success" : "warning"}>
                  {s.configured ? `configurado ${s.hint}` : "sin configurar"}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                {s.service} · {sourceLabel(s)}
              </p>
              <div className="flex gap-2">
                <Input
                  type="password"
                  autoComplete="off"
                  placeholder="Pegar valor nuevo…"
                  value={values[s.name] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [s.name]: e.target.value }))}
                />
                <Button
                  onClick={() => save.mutate(s.name)}
                  disabled={save.isPending || !(values[s.name] ?? "").trim()}
                >
                  Guardar
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  className="bg-muted text-foreground"
                  onClick={() => test.mutate(s.name)}
                  disabled={test.isPending}
                >
                  Probar
                </Button>
                {s.source === "app" && (
                  <Button
                    className="bg-transparent text-muted-foreground hover:bg-muted"
                    onClick={() => remove.mutate(s.name)}
                    disabled={remove.isPending}
                  >
                    Quitar
                  </Button>
                )}
                {testResults[s.name] && (
                  <span
                    className={`text-xs ${testResults[s.name].ok ? "text-emerald-500" : "text-red-500"}`}
                  >
                    {testResults[s.name].ok ? "✓" : "✗"} {testResults[s.name].detail}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {(audit.data?.entries.length ?? 0) > 0 && (
        <div>
          <p className="text-xs font-medium">Últimos cambios</p>
          <ul className="mt-1 space-y-0.5 text-[11px] text-muted-foreground">
            {audit.data!.entries.slice(0, 6).map((e, i) => (
              <li key={i}>
                {e.changed_at.slice(0, 16).replace("T", " ")} · {e.name} ·{" "}
                {e.action === "set" ? `guardado ${e.hint}` : "eliminado"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

export default function SettingsPage() {
  const [unitTypeId] = useActiveUnit();
  const test = useMutation({ mutationFn: () => api.testConnection() });

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-xl font-semibold">Configuración</h1>

      <Card className="space-y-2">
        <CardTitle>Integración Beds24</CardTitle>
        <CardDescription>Estado de la conexión con el Channel Manager.</CardDescription>
        <div className="flex items-center gap-2">
          <Button onClick={() => test.mutate()} disabled={test.isPending}>
            Comprobar
          </Button>
          {test.data && (
            <Badge variant={test.data.status === "connected" ? "success" : "warning"}>
              {test.data.status}
            </Badge>
          )}
        </div>
      </Card>

      <ChannelOffsetsCard />

      <SecretsCard />

      <Card className="space-y-1">
        <CardTitle>Modelo de LLM</CardTitle>
        <CardDescription>
          Modelos configurados en el servidor (.env): general para conversación y de acciones
          para escrituras. Las API keys se rotan en la tarjeta Secretos.
        </CardDescription>
      </Card>

      <Card className="space-y-1">
        <CardTitle>Preferencias</CardTitle>
        <CardDescription>Unidad activa: {unitTypeId} (se ajusta en Conexión).</CardDescription>
      </Card>
    </div>
  );
}
