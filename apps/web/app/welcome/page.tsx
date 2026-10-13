"use client";

import Link from "next/link";
import { SiteShell } from "@/components/site/site-shell";
import { Card, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/lib/i18n";

// Página pública de StayLever (feature 026): la "página principal" que muestra Google al
// entrar con Google, y la presentación para anfitriones invitados.
export default function WelcomePage() {
  const { m } = useI18n();
  const t = m.site.welcome;
  return (
    <SiteShell>
      <section className="space-y-4 py-8 text-center">
        <h1 className="text-3xl font-semibold leading-tight">{t.title}</h1>
        <p className="mx-auto max-w-xl text-muted-foreground">{t.lead}</p>
        <div className="flex flex-wrap justify-center gap-2">
          <Link href="/login" className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground">
            {t.cta}
          </Link>
          <Link href="/register" className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted">
            {t.ctaRegister}
          </Link>
        </div>
        <p className="text-xs text-muted-foreground">{t.beta}</p>
      </section>
      <section className="grid gap-3 sm:grid-cols-2">
        {t.features.map((f) => (
          <Card key={f.title} className="space-y-1">
            <CardTitle className="text-base">{f.title}</CardTitle>
            <p className="text-sm text-muted-foreground">{f.text}</p>
          </Card>
        ))}
      </section>
    </SiteShell>
  );
}
