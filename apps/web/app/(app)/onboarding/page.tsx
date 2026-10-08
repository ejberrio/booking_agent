"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useActiveUnit } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function OnboardingPage() {
  const { m } = useI18n();
  const t = m.connection;
  const [unitTypeId, setUnitTypeId] = useActiveUnit();
  const [unitInput, setUnitInput] = useState(String(unitTypeId));

  const test = useMutation({
    mutationFn: () => api.testConnection(),
    onError: () => toast.error(t.connect.failed),
  });
  const importRemote = useMutation({
    mutationFn: () => api.importRemote(),
    onSuccess: (r) => toast.success(t.import.done(r.created, r.issues)),
    onError: () => toast.error(t.import.failed),
  });

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-xl font-semibold">{t.title}</h1>

      <Card className="space-y-2">
        <CardTitle>{t.connect.title}</CardTitle>
        <CardDescription>{t.connect.description}</CardDescription>
        <Button onClick={() => test.mutate()} disabled={test.isPending}>
          {test.isPending ? t.connect.testing : t.connect.test}
        </Button>
        {test.data && (
          <p className="text-xs">
            {t.connect.status} <b>{t.statuses[test.data.status] ?? test.data.status}</b>
            {test.data.account ? ` · ${test.data.account}` : ""}
          </p>
        )}
      </Card>

      <Card className="space-y-2">
        <CardTitle>{t.import.title}</CardTitle>
        <CardDescription>{t.import.description}</CardDescription>
        <Button onClick={() => importRemote.mutate()} disabled={importRemote.isPending}>
          {importRemote.isPending ? t.import.running : t.import.run}
        </Button>
      </Card>

      <Card className="space-y-2">
        <CardTitle>{t.unit.title}</CardTitle>
        <CardDescription>{t.unit.description}</CardDescription>
        <div className="flex gap-2">
          <Label className="sr-only">{t.unit.label}</Label>
          <Input
            type="number"
            value={unitInput}
            onChange={(e) => setUnitInput(e.target.value)}
            className="w-32"
          />
          <Button
            onClick={() => {
              setUnitTypeId(Number(unitInput));
              toast.success(t.unit.saved);
            }}
          >
            {m.common.save}
          </Button>
        </div>
      </Card>
    </div>
  );
}
