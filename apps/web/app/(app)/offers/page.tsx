"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgePercent, ExternalLink, Tag, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useActiveUnit } from "@/lib/active-unit";
import { api, type PromotionInput } from "@/lib/api";
import { EXTERNAL_LINKS } from "@/lib/links";
import type { NativeDeal, NativeDealInput, PromotionPreview } from "@/lib/types";

const money = (v: string | null) =>
  v == null ? "—" : `${Number(v).toLocaleString("es-CO")} COP`;

export default function OffersPage() {
  const [unitTypeId] = useActiveUnit();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["promotions", unitTypeId],
    queryFn: () => api.listPromotions(unitTypeId),
  });

  const [form, setForm] = useState({
    name: "",
    first_night: "",
    last_night: "",
    discount_pct: "",
    min_nights: "",
  });
  // Alcance de canales: ambos marcados = todos (null); una selección parcial limita.
  const [scope, setScope] = useState<{ booking: boolean; airbnb: boolean }>({
    booking: true,
    airbnb: true,
  });
  const [preview, setPreview] = useState<PromotionPreview | null>(null);

  const refresh = () => qc.invalidateQueries({ queryKey: ["promotions", unitTypeId] });

  const scopeList = (): string[] | null => {
    const selected = (["booking", "airbnb"] as const).filter((c) => scope[c]);
    return selected.length === 2 ? null : selected;
  };
  const scopeLabel = (s: string[] | null | undefined) =>
    !s || s.length === 2
      ? "Todos los canales"
      : `Solo ${s.map((c) => (c === "booking" ? "Booking.com" : "Airbnb")).join(" y ")}`;

  const buildInput = (): PromotionInput => ({
    unit_type_id: unitTypeId,
    name: form.name.trim(),
    first_night: form.first_night,
    last_night: form.last_night,
    discount_pct: form.discount_pct ? Number(form.discount_pct) : null,
    min_nights: form.min_nights ? Number(form.min_nights) : null,
    channels_scope: scopeList(),
  });

  const previewM = useMutation({
    mutationFn: () => api.previewPromotion(buildInput()),
    onSuccess: setPreview,
    onError: (e: Error) => toast.error(e.message),
  });

  const applyM = useMutation({
    mutationFn: () =>
      api.applyPromotion({
        ...buildInput(),
        fingerprint: preview!.fingerprint,
        confirm_overlap: preview!.warnings.some((w) => w.includes("solapa")),
      }),
    onSuccess: (r) => {
      if (r.status === "published") toast.success("Promoción creada y publicada");
      else toast.warning(`Guardada, pero no se publicó: ${r.issue ?? "revisa incidencias"}`);
      setPreview(null);
      setForm({ name: "", first_night: "", last_night: "", discount_pct: "", min_nights: "" });
      refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const retireM = useMutation({
    mutationFn: (id: number) => api.retirePromotion(id),
    onSuccess: () => {
      toast("Promoción retirada");
      refresh();
    },
    onError: () => toast.error("No se pudo retirar"),
  });

  const active = data?.promotions.filter((p) => p.status !== "retired") ?? [];
  const retired = data?.promotions.filter((p) => p.status === "retired") ?? [];

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-xl font-semibold">Ofertas</h1>

      {/* Crear promoción de precio */}
      <Card>
        <CardTitle className="flex items-center gap-2">
          <Tag size={16} className="text-primary" /> Crear promoción de precio
        </CardTitle>
        <CardDescription>
          Una oferta con nombre y descuento sobre un rango de fechas. Se publica al Channel Manager.
          Revisa la propuesta antes de confirmar.
        </CardDescription>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <Label htmlFor="name">Nombre</Label>
            <Input
              id="name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Vacaciones enero"
            />
          </div>
          <div>
            <Label htmlFor="ff">Primera noche</Label>
            <Input
              id="ff"
              type="date"
              value={form.first_night}
              onChange={(e) => setForm({ ...form, first_night: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="ll">Última noche</Label>
            <Input
              id="ll"
              type="date"
              value={form.last_night}
              onChange={(e) => setForm({ ...form, last_night: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="pct">Descuento %</Label>
            <Input
              id="pct"
              type="number"
              value={form.discount_pct}
              onChange={(e) => setForm({ ...form, discount_pct: e.target.value })}
              placeholder="20"
            />
          </div>
          <div>
            <Label htmlFor="mn">Estancia mínima (opcional)</Label>
            <Input
              id="mn"
              type="number"
              value={form.min_nights}
              onChange={(e) => setForm({ ...form, min_nights: e.target.value })}
              placeholder="3"
            />
          </div>
          <div className="col-span-2">
            <Label>Canales donde aplica</Label>
            <div className="mt-1 flex gap-4 text-sm">
              {(["booking", "airbnb"] as const).map((c) => (
                <label key={c} className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={scope[c]}
                    onChange={(e) => setScope({ ...scope, [c]: e.target.checked })}
                  />
                  {c === "booking" ? "Booking.com" : "Airbnb"}
                </label>
              ))}
              <span className="text-xs text-muted-foreground self-center">
                (ambos = todos los canales)
              </span>
            </div>
          </div>
        </div>

        {preview ? (
          <div className="mt-4 rounded-md border border-border p-3 text-sm">
            <p className="font-medium">Propuesta</p>
            <p className="mt-1 text-muted-foreground">
              {preview.first_night} → {preview.last_night} · Base {money(preview.base_price)} →{" "}
              <strong className="text-foreground">{money(preview.price)}</strong>
              {preview.discount_pct ? ` (${preview.discount_pct}%)` : ""} · Ahorro{" "}
              {money(preview.saving)}
            </p>
            <p className="mt-1 text-muted-foreground">
              Estancia mínima:{" "}
              <strong className="text-foreground">
                {preview.min_nights ? `${preview.min_nights} noches` : "sin mínimo"}
              </strong>{" "}
              · Alcance:{" "}
              <strong className="text-foreground">{scopeLabel(preview.channels_scope)}</strong>
            </p>
            {preview.warnings.map((w) => (
              <p key={w} className="mt-1 text-amber-600">
                ⚠️ {w}
              </p>
            ))}
            <div className="mt-3 flex gap-2">
              <Button onClick={() => applyM.mutate()} disabled={applyM.isPending}>
                Confirmar y publicar
              </Button>
              <Button
                className="bg-transparent text-muted-foreground hover:bg-muted"
                onClick={() => setPreview(null)}
              >
                Cancelar
              </Button>
            </div>
          </div>
        ) : (
          <Button
            className="mt-4"
            onClick={() => previewM.mutate()}
            disabled={previewM.isPending || !form.name || !form.first_night || !form.last_night}
          >
            Ver propuesta
          </Button>
        )}
      </Card>

      {/* Promociones existentes */}
      <Card>
        <CardTitle>Mis promociones</CardTitle>
        {isLoading ? (
          <Skeleton className="mt-3 h-16 w-full" />
        ) : !active.length && !retired.length ? (
          <CardDescription className="mt-2">
            Aún no tienes promociones. Crea una arriba o pídela por el{" "}
            <a className="underline" href="/chat">chat</a>.
          </CardDescription>
        ) : (
          <div className="mt-3 space-y-2">
            {active.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded-md border border-border p-3 text-sm"
              >
                <div>
                  <div className="font-medium">{p.name}</div>
                  <div className="text-muted-foreground">
                    {p.first_night} → {p.last_night} · {money(p.price)}
                    {p.saving ? ` · ahorro ${money(p.saving)}` : ""}
                    {p.min_nights ? ` · mín ${p.min_nights} noches` : ""}
                    {" · "}
                    {scopeLabel(p.channels_scope)}
                  </div>
                  {p.status === "sync_error" ? (
                    <div className="text-amber-600">No publicada (incidencia de sincronización)</div>
                  ) : null}
                </div>
                <Button
                  className="bg-transparent px-2 text-muted-foreground hover:bg-muted"
                  onClick={() => retireM.mutate(p.id)}
                  disabled={retireM.isPending}
                >
                  <Trash2 size={14} /> Retirar
                </Button>
              </div>
            ))}
            {retired.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground"
              >
                <span>
                  {p.name} · {p.first_night} → {p.last_night} (retirada)
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Guía: qué se gestiona dónde (3 vías) */}
      <Card>
        <CardTitle className="flex items-center gap-2">
          <BadgePercent size={16} className="text-amber-500" /> ¿Y los deals nativos de los canales?
        </CardTitle>
        <CardDescription>
          Hay tres tipos de descuento y cada uno se gestiona en su sitio:{" "}
          <strong>1) Promociones de precio</strong> (arriba): baja el precio en los canales que
          elijas, sin badge. <strong>2) Deals con badge de Booking</strong> (Basic Deal, Última
          hora, Genius): en Beds24, sincronizan con Booking.{" "}
          <strong>3) Descuentos de Airbnb</strong> (semanal, mensual, promos del anuncio): en
          Airbnb.
        </CardDescription>
        <div className="mt-3 flex flex-wrap gap-2">
          <a
            href={EXTERNAL_LINKS.beds24BookingPromotions}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground"
          >
            Deals de Booking en Beds24 <ExternalLink size={14} />
          </a>
          <a
            href={EXTERNAL_LINKS.airbnbMulticalendar}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground"
          >
            Descuentos del anuncio en Airbnb <ExternalLink size={14} />
          </a>
          <a
            href={EXTERNAL_LINKS.beds24AirbnbPromotions}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm text-foreground"
          >
            Promotions de Airbnb en Beds24 <ExternalLink size={14} />
          </a>
          <a
            href={EXTERNAL_LINKS.bookingExtranet}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm text-foreground"
          >
            Extranet de Booking <ExternalLink size={14} />
          </a>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          ⚠️ No combines un deal nativo (badge de Booking o descuento de Airbnb) con una promoción
          de precio para las mismas fechas y el mismo canal: el descuento se duplicaría. En Airbnb,
          una promoción de precio recibe además el ajuste del canal si lo tienes configurado.
        </p>
      </Card>

      <NativeDealsCard />
    </div>
  );
}

const DEAL_CHANNELS = { booking: "Booking.com", airbnb: "Airbnb" } as const;

function dealVigencia(d: NativeDeal): string {
  if (!d.date_from && !d.date_to) return "siempre activo";
  if (d.date_from && d.date_to) return `${d.date_from} → ${d.date_to}`;
  return d.date_from ? `desde ${d.date_from}` : `hasta ${d.date_to}`;
}

/** Registro informativo de deals nativos (feature 015). No escribe nada al canal:
 *  el deal se crea/gestiona en el panel (enlaces de arriba) y aquí se ANOTA para
 *  verlo en el calendario y activar la advertencia real de doble descuento. */
function NativeDealsCard() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["native-deals"],
    queryFn: () => api.listNativeDeals(),
  });
  const empty = { channel: "booking" as "booking" | "airbnb", name: "", pct: "", from: "", to: "" };
  const [form, setForm] = useState(empty);
  const [editingId, setEditingId] = useState<number | null>(null);

  const refresh = () => qc.invalidateQueries({ queryKey: ["native-deals"] });
  const onError = (e: Error) => toast.error(e.message);

  const buildInput = (): NativeDealInput => ({
    channel: form.channel,
    name: form.name.trim(),
    discount_pct: Number(form.pct),
    date_from: form.from || null,
    date_to: form.to || null,
  });

  const save = useMutation({
    mutationFn: () =>
      editingId === null
        ? api.createNativeDeal(buildInput())
        : api.updateNativeDeal(editingId, buildInput()),
    onSuccess: () => {
      toast.success(editingId === null ? "Deal anotado" : "Deal actualizado");
      setForm(empty);
      setEditingId(null);
      refresh();
    },
    onError,
  });
  const toggle = useMutation({
    mutationFn: (d: NativeDeal) => api.updateNativeDeal(d.id, { is_active: !d.is_active }),
    onSuccess: refresh,
    onError,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteNativeDeal(id),
    onSuccess: () => {
      toast("Deal borrado del registro");
      refresh();
    },
    onError,
  });

  const deals = data?.deals ?? [];

  return (
    <Card>
      <CardTitle>Deals nativos registrados</CardTitle>
      <CardDescription>
        Cuando crees o quites un deal en el panel del canal (enlaces de arriba), anótalo aquí:
        la app lo marca en el calendario y te avisa si una promoción tuya duplicaría el
        descuento. Este registro NO cambia nada en el canal.
      </CardDescription>

      {isLoading ? (
        <Skeleton className="mt-3 h-16 w-full" />
      ) : deals.length ? (
        <div className="mt-3 space-y-2">
          {deals.map((d) => (
            <div
              key={d.id}
              className="flex items-center justify-between rounded-md border border-border p-3 text-sm"
            >
              <div className={d.is_active ? "" : "opacity-50"}>
                <div className="font-medium">{d.name}</div>
                <div className="text-muted-foreground">
                  {DEAL_CHANNELS[d.channel]} · {Number(d.discount_pct)}% · {dealVigencia(d)}
                  {d.is_active ? "" : " · inactivo"}
                </div>
              </div>
              <div className="flex gap-1">
                <Button
                  className="bg-transparent px-2 text-muted-foreground hover:bg-muted"
                  onClick={() => toggle.mutate(d)}
                  disabled={toggle.isPending}
                >
                  {d.is_active ? "Desactivar" : "Reactivar"}
                </Button>
                <Button
                  className="bg-transparent px-2 text-muted-foreground hover:bg-muted"
                  onClick={() => {
                    setEditingId(d.id);
                    setForm({
                      channel: d.channel,
                      name: d.name,
                      pct: String(Number(d.discount_pct)),
                      from: d.date_from ?? "",
                      to: d.date_to ?? "",
                    });
                  }}
                >
                  Editar
                </Button>
                <Button
                  className="bg-transparent px-2 text-muted-foreground hover:bg-muted"
                  onClick={() => remove.mutate(d.id)}
                  disabled={remove.isPending}
                >
                  <Trash2 size={14} />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <CardDescription className="mt-2">
          Sin deals anotados. Registra los que tengas activos en Booking/Airbnb.
        </CardDescription>
      )}

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="dch">Canal</Label>
          <select
            id="dch"
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={form.channel}
            onChange={(e) => setForm({ ...form, channel: e.target.value as "booking" | "airbnb" })}
          >
            <option value="booking">Booking.com</option>
            <option value="airbnb">Airbnb</option>
          </select>
        </div>
        <div>
          <Label htmlFor="dpct">Descuento %</Label>
          <Input
            id="dpct"
            type="number"
            value={form.pct}
            onChange={(e) => setForm({ ...form, pct: e.target.value })}
            placeholder="20"
          />
        </div>
        <div className="col-span-2">
          <Label htmlFor="dname">Nombre</Label>
          <Input
            id="dname"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Vacaciones Julio · mín 3"
          />
        </div>
        <div>
          <Label htmlFor="dfrom">Desde (vacío = siempre)</Label>
          <Input
            id="dfrom"
            type="date"
            value={form.from}
            onChange={(e) => setForm({ ...form, from: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="dto">Hasta (vacío = siempre)</Label>
          <Input
            id="dto"
            type="date"
            value={form.to}
            onChange={(e) => setForm({ ...form, to: e.target.value })}
          />
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <Button
          onClick={() => save.mutate()}
          disabled={save.isPending || !form.name.trim() || !form.pct}
        >
          {editingId === null ? "Anotar deal" : "Guardar cambios"}
        </Button>
        {editingId !== null && (
          <Button
            className="bg-transparent text-muted-foreground hover:bg-muted"
            onClick={() => {
              setEditingId(null);
              setForm(empty);
            }}
          >
            Cancelar
          </Button>
        )}
      </div>
    </Card>
  );
}
