"use client";

import { PlugZap } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useUnits } from "@/lib/active-unit";
import { useI18n } from "@/lib/i18n";

/** Muestra la página solo si la cuenta tiene unidades (feature 026).
 *
 *  Cuenta nueva sin channel manager → mensaje claro con el camino a Ajustes, en vez de
 *  pantallas que fallan. Si la lista no se pudo cargar, se muestra la página igual (cada
 *  consulta informa su propio error, como antes).
 */
export function UnitGate({ children }: { children: React.ReactNode }) {
  const { m } = useI18n();
  const { data, isLoading, isError } = useUnits();
  if (isLoading) {
    return <p className="p-6 text-sm text-muted-foreground">{m.account.loadingUnits}</p>;
  }
  if (!isError && data && data.length === 0) {
    return (
      <div className="mx-auto mt-10 max-w-md space-y-3 rounded-xl border bg-card p-6 text-center">
        <PlugZap className="mx-auto text-primary" size={28} />
        <h2 className="text-lg font-semibold">{m.account.emptyTitle}</h2>
        <p className="text-sm text-muted-foreground">{m.account.emptyText}</p>
        <Link href="/settings" className="inline-block">
          <Button>{m.account.emptyCta}</Button>
        </Link>
      </div>
    );
  }
  return <>{children}</>;
}
