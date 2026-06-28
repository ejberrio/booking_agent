"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import type { AvailabilityAction, AvailabilityPreview, ChangePreview } from "@/lib/types";

interface Props {
  unitTypeId: number;
  selection: { from: string; to: string } | null;
  onApplied: () => void;
}

export function RangeEditor({ unitTypeId, selection, onApplied }: Props) {
  const [price, setPrice] = useState("");
  const [preview, setPreview] = useState<ChangePreview | null>(null);
  const [busy, setBusy] = useState(false);

  // Disponibilidad (bloquear/abrir)
  const [availPreview, setAvailPreview] = useState<AvailabilityPreview | null>(null);
  const [availAction, setAvailAction] = useState<AvailabilityAction>("block");

  async function doPreview() {
    if (!selection || !price) return;
    setBusy(true);
    try {
      const p = await api.previewRange({
        unit_type_id: unitTypeId,
        selection: { date_from: selection.from, date_to: selection.to },
        price: Number(price),
      });
      setPreview(p);
    } catch {
      toast.error("No se pudo previsualizar");
    } finally {
      setBusy(false);
    }
  }

  async function doApply() {
    if (!selection || !preview) return;
    setBusy(true);
    try {
      const res = await api.applyRange({
        unit_type_id: unitTypeId,
        selection: { date_from: selection.from, date_to: selection.to },
        price: Number(price),
        fingerprint: preview.fingerprint,
      });
      if (res.stale) {
        toast.warning("El estado cambió; vuelve a previsualizar");
        await doPreview();
        return;
      }
      toast.success(`Aplicado a ${res.applied_days.length} día(s)`);
      setPreview(null);
      setPrice("");
      onApplied();
    } catch {
      toast.error("No se pudo aplicar");
    } finally {
      setBusy(false);
    }
  }

  async function doAvailPreview(action: AvailabilityAction) {
    if (!selection) return;
    setAvailAction(action);
    setBusy(true);
    try {
      const p = await api.availabilityPreview({
        unit_type_id: unitTypeId,
        action,
        selection: { date_from: selection.from, date_to: selection.to },
      });
      setAvailPreview(p);
    } catch {
      toast.error("No se pudo previsualizar");
    } finally {
      setBusy(false);
    }
  }

  async function doAvailApply() {
    if (!selection || !availPreview) return;
    setBusy(true);
    try {
      const res = await api.availabilityApply({
        unit_type_id: unitTypeId,
        action: availAction,
        selection: { date_from: selection.from, date_to: selection.to },
        fingerprint: availPreview.fingerprint,
      });
      if (res.stale) {
        toast.warning("El estado cambió; vuelve a previsualizar");
        await doAvailPreview(availAction);
        return;
      }
      const verbo = availAction === "block" ? "Bloqueadas" : "Reabiertas";
      toast.success(`${verbo} ${res.applied.length} noche(s)`);
      setAvailPreview(null);
      onApplied();
    } catch {
      toast.error("No se pudo aplicar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <Label>Editar rango</Label>
      <p className="mb-2 mt-1 text-xs text-muted-foreground">
        {selection ? `${selection.from} → ${selection.to}` : "Selecciona días en el calendario"}
      </p>

      <div className="flex gap-2">
        <Input
          type="number"
          placeholder="Precio (COP)"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          disabled={!selection}
        />
        <Button onClick={doPreview} disabled={!selection || !price || busy}>
          Precio
        </Button>
      </div>

      <p className="mb-1 mt-4 text-xs font-medium">Disponibilidad</p>
      <div className="flex gap-2">
        <Button
          className="bg-muted text-foreground"
          onClick={() => doAvailPreview("block")}
          disabled={!selection || busy}
        >
          Bloquear
        </Button>
        <Button
          className="bg-muted text-foreground"
          onClick={() => doAvailPreview("open")}
          disabled={!selection || busy}
        >
          Abrir
        </Button>
      </div>

      {/* Diálogo de precio */}
      <Dialog open={preview !== null} onClose={() => setPreview(null)}>
        {preview && (
          <div>
            <h3 className="text-sm font-semibold">Previsualización del precio</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              {preview.valid_count} día(s) a aplicar
              {preview.invalid_count ? `, ${preview.invalid_count} fuera de límites` : ""}.
            </p>
            <div className="mt-3 max-h-64 space-y-1 overflow-y-auto text-xs">
              {preview.items.map((it) => (
                <div
                  key={it.date}
                  className="flex items-center justify-between rounded-md border border-border px-2 py-1"
                >
                  <span>{it.date}</span>
                  <span className={it.valid ? "" : "text-red-500"}>
                    {formatCOP(it.old_price)} → {formatCOP(it.new_price)}
                    {it.valid ? "" : " (inválido)"}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                className="bg-muted text-foreground"
                onClick={() => setPreview(null)}
                disabled={busy}
              >
                Cancelar
              </Button>
              <Button onClick={doApply} disabled={busy || preview.valid_count === 0}>
                Confirmar
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* Diálogo de disponibilidad */}
      <Dialog open={availPreview !== null} onClose={() => setAvailPreview(null)}>
        {availPreview && (
          <div>
            <h3 className="text-sm font-semibold">
              {availAction === "block" ? "Bloquear" : "Abrir"} disponibilidad
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              {availPreview.affected_count} noche(s) a {availAction === "block" ? "bloquear" : "abrir"}
              {availPreview.skipped_count ? `, ${availPreview.skipped_count} omitida(s)` : ""}.
            </p>
            <div className="mt-3 max-h-64 space-y-1 overflow-y-auto text-xs">
              {availPreview.items.map((it) => (
                <div
                  key={it.date}
                  className="flex items-center justify-between rounded-md border border-border px-2 py-1"
                >
                  <span>{it.date}</span>
                  <span className={it.valid ? "" : "text-muted-foreground"}>
                    {it.valid
                      ? availAction === "block"
                        ? "bloquear"
                        : "abrir"
                      : `omitida (${it.skip_reason})`}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                className="bg-muted text-foreground"
                onClick={() => setAvailPreview(null)}
                disabled={busy}
              >
                Cancelar
              </Button>
              <Button onClick={doAvailApply} disabled={busy || availPreview.affected_count === 0}>
                Confirmar
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </Card>
  );
}
