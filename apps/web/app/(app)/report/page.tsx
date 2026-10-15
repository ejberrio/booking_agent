"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { EventRow } from "@/components/site/free-report";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { useUnits } from "@/lib/active-unit";
import { api } from "@/lib/api";
import { formatCOP } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

// Informe completo de la cuenta creada desde la página pública (feature 030).
export default function MyReportPage() {
  const { m, lang } = useI18n();
  const t = m.pub.app;
  const q = useQuery({ queryKey: ["my-report"], queryFn: api.myReport, retry: false });
  const units = useUnits();

  if (q.isLoading) return null;
  if (!q.data) {
    return (
      <Card>
        <CardDescription>{t.empty}</CardDescription>
      </Card>
    );
  }
  const r = q.data;
  return (
    <div className="mx-auto max-w-2xl space-y-3">
      <Card className="space-y-3">
        <CardTitle className="text-base">{t.title}</CardTitle>
        <CardDescription>{t.lead(r.municipality.label, formatCOP(r.weekday_price, lang))}</CardDescription>
        {r.events.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t.empty}</p>
        ) : (
          <ul className="divide-y divide-border">
            {r.events.map((ev) => <EventRow key={`${ev.name}-${ev.start_date}`} ev={ev} />)}
          </ul>
        )}
        <p className="text-xs text-muted-foreground">{m.pub.report.disclaimer}</p>
      </Card>
      {units.data && units.data.length === 0 && (
        <Link href="/setup/manual"
          className="block rounded-md bg-primary px-4 py-2.5 text-center text-sm font-medium text-primary-foreground">
          {t.setupCta}
        </Link>
      )}
    </div>
  );
}
