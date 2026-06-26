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
import type { ChangePreview } from "@/lib/types";

interface Props {
  unitTypeId: number;
  selection: { from: string; to: string } | null;
  onApplied: () => void;
}

export function RangeEditor({ unitTypeId, selection, onApplied }: Props) {
  const [price, setPrice] = useState("");
  const [preview, setPreview] = useState<ChangePreview | null>(null);
  const [busy, setBusy] = useState(false);

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

  return (
    <Card>
      <Label>Editar precio del rango</Label>
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
          Previsualizar
        </Button>
      </div>

      <Dialog open={preview !== null} onClose={() => setPreview(null)}>
        {preview && (
          <div>
            <h3 className="text-sm font-semibold">Previsualización del cambio</h3>
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
    </Card>
  );
}
