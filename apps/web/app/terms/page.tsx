"use client";

import { SiteShell } from "@/components/site/site-shell";
import { useI18n } from "@/lib/i18n";

// Términos de uso públicos (feature 028): incluyen el encargo del tratamiento de los datos
// de los huéspedes (el anfitrión es Responsable; StayLever, Encargado).
export default function TermsPage() {
  const { m } = useI18n();
  const t = m.terms;
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
