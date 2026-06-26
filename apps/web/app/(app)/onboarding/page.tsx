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

export default function OnboardingPage() {
  const [unitTypeId, setUnitTypeId] = useActiveUnit();
  const [unitInput, setUnitInput] = useState(String(unitTypeId));

  const test = useMutation({
    mutationFn: () => api.testConnection(),
    onError: () => toast.error("No se pudo conectar a Beds24"),
  });
  const importRemote = useMutation({
    mutationFn: () => api.importRemote(),
    onSuccess: (r) => toast.success(`Importación: ${r.created} creados, ${r.issues} incidencias`),
    onError: () => toast.error("Falló la importación"),
  });

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="text-xl font-semibold">Conexión y onboarding</h1>

      <Card className="space-y-2">
        <CardTitle>1. Conectar Beds24</CardTitle>
        <CardDescription>Verifica que las credenciales del .env funcionan.</CardDescription>
        <Button onClick={() => test.mutate()} disabled={test.isPending}>
          {test.isPending ? "Probando…" : "Probar conexión"}
        </Button>
        {test.data && (
          <p className="text-xs">
            Estado: <b>{test.data.status}</b>
            {test.data.account ? ` · ${test.data.account}` : ""}
          </p>
        )}
      </Card>

      <Card className="space-y-2">
        <CardTitle>2. Importar datos</CardTitle>
        <CardDescription>Trae propiedades, precios y reservas desde Beds24.</CardDescription>
        <Button onClick={() => importRemote.mutate()} disabled={importRemote.isPending}>
          {importRemote.isPending ? "Importando…" : "Importar ahora"}
        </Button>
      </Card>

      <Card className="space-y-2">
        <CardTitle>3. Propiedad activa</CardTitle>
        <CardDescription>Id de la unidad a gestionar (tras importar).</CardDescription>
        <div className="flex gap-2">
          <Label className="sr-only">Unidad</Label>
          <Input
            type="number"
            value={unitInput}
            onChange={(e) => setUnitInput(e.target.value)}
            className="w-32"
          />
          <Button
            onClick={() => {
              setUnitTypeId(Number(unitInput));
              toast.success("Unidad activa guardada");
            }}
          >
            Guardar
          </Button>
        </div>
      </Card>
    </div>
  );
}
