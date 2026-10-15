"use client";

import Link from "next/link";
import { useEffect } from "react";
import { FreeReport } from "@/components/site/free-report";
import { SiteShell } from "@/components/site/site-shell";
import { Card } from "@/components/ui/card";
import { useI18n } from "@/lib/i18n";

// Página pública de StayLever (feature 030): portada para quien llega sin sesión, con el
// informe gratis. También es la "página principal" que muestra Google al entrar con Google.
function useVisit() {
  useEffect(() => {
    // Una visita por pestaña, sin cookies ni identificadores (contador diario agregado).
    try {
      if (sessionStorage.getItem("sl_visit")) return;
      sessionStorage.setItem("sl_visit", "1");
    } catch {
      return;
    }
    void fetch("/api/public/visit", { method: "POST" }).catch(() => undefined);
  }, []);
}

function SuggestionMock() {
  const { m } = useI18n();
  const t = m.pub.mock;
  return (
    <div className="space-y-3" aria-hidden="true">
      <Card className="space-y-2 text-left shadow-sm">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{t.night}</span>
          <span className="rounded bg-red-500/15 px-1.5 py-0.5 text-red-600 dark:text-red-400">+30%</span>
        </div>
        <p className="text-sm font-medium">{t.event}</p>
        <p className="text-2xl font-semibold">
          <span className="mr-2 text-base font-normal text-muted-foreground line-through">$250.000</span>
          $325.000
        </p>
        <p className="text-xs text-muted-foreground">{t.reason}</p>
        <div className="flex gap-2 pt-1">
          <span className="rounded-md bg-primary px-3 py-1 text-xs text-primary-foreground">{t.approve}</span>
          <span className="rounded-md border border-border px-3 py-1 text-xs">{t.dismiss}</span>
        </div>
      </Card>
      <div className="space-y-2 text-sm">
        <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-primary-foreground">
          {t.chat}
        </p>
        <p className="w-fit max-w-[85%] rounded-2xl rounded-bl-sm bg-muted px-3 py-2">{t.chatReply}</p>
      </div>
    </div>
  );
}

export default function WelcomePage() {
  const { m } = useI18n();
  const t = m.pub;
  useVisit();
  return (
    <SiteShell>
      <section className="grid items-center gap-8 py-8 md:grid-cols-[1.2fr_1fr]">
        <div className="space-y-4">
          <span className="inline-block rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            {t.hero.badge}
          </span>
          <h1 className="text-3xl font-semibold leading-tight sm:text-4xl">{t.hero.title}</h1>
          <p className="text-muted-foreground">{t.hero.lead}</p>
          <div className="flex flex-wrap gap-2">
            <a href="#informe" className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
              {t.hero.ctaReport}
            </a>
            <Link href="/register" className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted">
              {t.hero.ctaJoin}
            </Link>
          </div>
          <p className="text-xs text-muted-foreground">{t.hero.note}</p>
        </div>
        <SuggestionMock />
      </section>

      <section className="space-y-3 py-6">
        <h2 className="text-xl font-semibold">{t.who.title}</h2>
        <ul className="space-y-2">
          {t.who.items.map((item) => (
            <li key={item} className="flex gap-2 text-sm">
              <span className="text-primary">✓</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3 py-6">
        <h2 className="text-xl font-semibold">{t.how.title}</h2>
        <ol className="grid gap-3 sm:grid-cols-3">
          {t.how.steps.map((s, i) => (
            <li key={s.title}>
              <Card className="h-full space-y-1">
                <span className="text-xs font-semibold text-primary">{i + 1}</span>
                <h3 className="font-medium">{s.title}</h3>
                <p className="text-sm text-muted-foreground">{s.text}</p>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      <section id="informe" className="scroll-mt-4 space-y-3 py-6">
        <h2 className="text-xl font-semibold">{t.report.title}</h2>
        <p className="text-sm text-muted-foreground">{t.report.lead}</p>
        <FreeReport />
      </section>

      <section className="space-y-3 py-6">
        <h2 className="text-xl font-semibold">{t.faq.title}</h2>
        <div className="divide-y divide-border rounded-xl border border-border">
          {t.faq.items.map((f) => (
            <details key={f.q} className="group px-4 py-3">
              <summary className="cursor-pointer list-none font-medium">
                <span className="mr-2 inline-block transition-transform group-open:rotate-90">›</span>
                {f.q}
              </summary>
              <p className="mt-2 text-sm text-muted-foreground">{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="space-y-3 py-8 text-center">
        <h2 className="text-xl font-semibold">{t.footerCta}</h2>
        <div className="flex flex-wrap justify-center gap-2">
          <a href="#informe" className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
            {t.hero.ctaReport}
          </a>
          <Link href="/register" className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted">
            {t.hero.ctaJoin}
          </Link>
        </div>
      </section>
    </SiteShell>
  );
}
