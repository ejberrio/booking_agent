"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** Resumen semanal por correo (feature 030): activar o desactivar. */
export function DigestCard() {
  const { m } = useI18n();
  const t = m.pub.digest;
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["digest"], queryFn: api.digest });
  const set = useMutation({
    mutationFn: api.setDigest,
    onSuccess: (d) => qc.setQueryData(["digest"], d),
    onError: (e: Error) => toast.error(e.message),
  });
  if (!q.data?.available) return null;
  const on = q.data.enabled;
  return (
    <Card className="space-y-2">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.text}</CardDescription>
      <div className="flex gap-2">
        <Button className={on ? "" : "bg-muted text-foreground"} onClick={() => set.mutate(true)}
          disabled={set.isPending || on}>
          {t.on}
        </Button>
        <Button className={!on ? "" : "bg-muted text-foreground"} onClick={() => set.mutate(false)}
          disabled={set.isPending || !on}>
          {t.off}
        </Button>
      </div>
    </Card>
  );
}
