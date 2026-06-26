"use client";

import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { useActiveUnit } from "@/lib/active-unit";
import { api } from "@/lib/api";

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

      <Card className="space-y-1">
        <CardTitle>Modelo de LLM</CardTitle>
        <CardDescription>
          Configurado en el servidor (.env): modelo general para conversación y modelo de acciones
          para escrituras. Las claves nunca se muestran aquí.
        </CardDescription>
        <p className="text-xs text-muted-foreground">
          Edición desde la UI: pendiente de un endpoint de configuración en el backend.
        </p>
      </Card>

      <Card className="space-y-1">
        <CardTitle>Preferencias</CardTitle>
        <CardDescription>Unidad activa: {unitTypeId} (se ajusta en Conexión).</CardDescription>
      </Card>
    </div>
  );
}
