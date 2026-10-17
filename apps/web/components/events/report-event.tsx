"use client";

import { useQueryClient } from "@tanstack/react-query";
import { CalendarPlus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** "¿Falta un evento?" (feature 035): el anfitrión reporta un evento; StayLever lo verifica. */
export function ReportEvent() {
  const { m } = useI18n();
  const t = m.events;
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", start: "", end: "", venue: "" });
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ status: string; message: string } | null>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setF({ ...f, [k]: e.target.value });

  function close() {
    setOpen(false);
    setResult(null);
    setF({ name: "", start: "", end: "", venue: "" });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api.reportEvent({
        name: f.name.trim(),
        start_date: f.start,
        end_date: f.end || undefined,
        venue: f.venue.trim() || undefined,
      });
      setResult(r);
      if (r.status === "verified") await qc.invalidateQueries();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const label = result
    ? { exists: t.exists, verified: t.verified, unverified: t.unverified }[result.status] ?? ""
    : "";

  return (
    <>
      <Button className="bg-muted text-foreground" onClick={() => setOpen(true)}>
        <CalendarPlus size={16} className="mr-1" /> {t.button}
      </Button>
      <Dialog open={open} onClose={close}>
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">{t.title}</h2>
          {result ? (
            <div className="space-y-3">
              <p className="text-sm font-medium">{label}</p>
              <p className="text-sm text-muted-foreground">{result.message}</p>
              <Button onClick={close}>{t.close}</Button>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-3">
              <p className="text-sm text-muted-foreground">{t.text}</p>
              <Input placeholder={t.name} value={f.name} onChange={set("name")} required
                minLength={3} maxLength={200} />
              <div className="grid grid-cols-2 gap-2">
                <label className="space-y-1 text-xs text-muted-foreground">
                  <span>{t.start}</span>
                  <Input type="date" value={f.start} onChange={set("start")} required />
                </label>
                <label className="space-y-1 text-xs text-muted-foreground">
                  <span>{t.end}</span>
                  <Input type="date" value={f.end} onChange={set("end")} min={f.start} />
                </label>
              </div>
              <Input placeholder={t.venue} value={f.venue} onChange={set("venue")} maxLength={200} />
              <p className="text-xs text-muted-foreground">{t.limit}</p>
              <div className="flex gap-2">
                <Button type="submit" disabled={busy || f.name.trim().length < 3 || !f.start}>
                  {busy ? t.checking : t.submit}
                </Button>
                <Button type="button" className="bg-muted text-foreground" onClick={close}>
                  {t.close}
                </Button>
              </div>
            </form>
          )}
        </div>
      </Dialog>
    </>
  );
}
