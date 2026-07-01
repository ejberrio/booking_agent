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
import type { PromotionPreview } from "@/lib/types";

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
  const [preview, setPreview] = useState<PromotionPreview | null>(null);

  const refresh = () => qc.invalidateQueries({ queryKey: ["promotions", unitTypeId] });

  const buildInput = (): PromotionInput => ({
    unit_type_id: unitTypeId,
    name: form.name.trim(),
    first_night: form.first_night,
    last_night: form.last_night,
    discount_pct: form.discount_pct ? Number(form.discount_pct) : null,
    min_nights: form.min_nights ? Number(form.min_nights) : null,
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
              </strong>
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

      {/* Distinción con los deals nativos de Booking */}
      <Card>
        <CardTitle className="flex items-center gap-2">
          <BadgePercent size={16} className="text-amber-500" /> ¿Y los deals con badge de Booking?
        </CardTitle>
        <CardDescription>
          Los <strong>deals con etiqueta/badge</strong> (Basic Deal, Última hora, Early Booker,
          Genius) que el huésped ve en tu anuncio <strong>no se gestionan por API</strong>: se crean
          en el panel de Beds24 o en el extranet de Booking.
        </CardDescription>
        <div className="mt-3 flex flex-wrap gap-2">
          <a
            href={EXTERNAL_LINKS.beds24Dashboard}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground"
          >
            Panel de Beds24 <ExternalLink size={14} />
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
      </Card>
    </div>
  );
}
