import { Card } from "@/components/ui/card";

// Indicador del Panorama (rediseño #195): etiqueta, cifra en Fraunces y pista opcional.
export function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card>
      <p className="text-sm font-semibold text-muted-foreground">{label}</p>
      <p className="mt-1 font-display text-3xl font-semibold">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </Card>
  );
}
