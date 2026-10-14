"use client";

import { useI18n } from "@/lib/i18n";

export type LegalKind = "terms" | "privacy";

/** Texto de los Términos o la Política de privacidad (páginas públicas y ventana de lectura). */
export function LegalDoc({ kind }: { kind: LegalKind }) {
  const { m } = useI18n();
  const t = kind === "terms" ? m.terms : m.site.privacy;
  return (
    <article className="space-y-6">
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
  );
}
