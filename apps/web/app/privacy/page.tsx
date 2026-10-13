"use client";

import { SiteShell } from "@/components/site/site-shell";
import { useI18n } from "@/lib/i18n";

// Política de privacidad pública (feature 026; Google la exige para "Entrar con Google").
export default function PrivacyPage() {
  const { m } = useI18n();
  const t = m.site.privacy;
  return (
    <SiteShell>
      <article className="space-y-6 py-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold">{t.title}</h1>
          <p className="text-xs text-muted-foreground">{t.updated}</p>
        </header>
        {t.sections.map((s) => (
          <section key={s.title} className="space-y-2">
            <h2 className="text-lg font-medium">{s.title}</h2>
            {s.body.map((p, i) => (
              <p key={i} className="text-sm leading-relaxed text-muted-foreground">{p}</p>
            ))}
          </section>
        ))}
      </article>
    </SiteShell>
  );
}
