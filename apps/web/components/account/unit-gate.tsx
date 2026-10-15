"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, Home, PlugZap } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useUnits } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** Muestra la página solo si la cuenta tiene unidades (feature 026).
 *
 *  Cuenta nueva → dos caminos (feature 029): conectar el channel manager o crear el
 *  apartamento a mano (modo sin conexión). Si la lista no se pudo cargar, se muestra la
 *  página igual (cada consulta informa su propio error, como antes).
 */
export function UnitGate({ children }: { children: React.ReactNode }) {
  const { m } = useI18n();
  const t = m.offline.gate;
  const { data, isLoading, isError } = useUnits();
  const empty = !isError && !!data && data.length === 0;
  // Feature 030: cuenta creada desde el informe gratis → enlace a su informe completo.
  const report = useQuery({ queryKey: ["my-report"], queryFn: api.myReport, retry: false, enabled: empty });
  if (isLoading) {
    return <p className="p-6 text-sm text-muted-foreground">{m.account.loadingUnits}</p>;
  }
  if (!isError && data && data.length === 0) {
    return (
      <div className="mx-auto mt-10 max-w-2xl space-y-4">
        <h2 className="text-center text-lg font-semibold">{t.title}</h2>
        {report.data && (
          <Link href="/report"
            className="flex items-center justify-center gap-2 rounded-xl border border-primary/40 bg-primary/5 p-3 text-sm font-medium text-primary">
            <FileText size={16} />
            {m.pub.app.seeReport}
          </Link>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-3 rounded-xl border bg-card p-5">
            <Home className="text-primary" size={24} />
            <h3 className="font-semibold">{t.manualTitle}</h3>
            <p className="text-sm text-muted-foreground">{t.manualText}</p>
            <Link href="/setup/manual" className="inline-block">
              <Button>{t.manualCta}</Button>
            </Link>
          </div>
          <div className="space-y-3 rounded-xl border bg-card p-5">
            <PlugZap className="text-primary" size={24} />
            <h3 className="font-semibold">{t.connectTitle}</h3>
            <p className="text-sm text-muted-foreground">{t.connectText}</p>
            <Link href="/settings" className="inline-block">
              <Button className="bg-muted text-foreground">{t.connectCta}</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
