"use client";

import Link from "next/link";
import { Logo } from "@/components/brand/logo";
import { LanguageSwitcher } from "@/components/i18n/language-switcher";
import { useI18n } from "@/lib/i18n";

/** Marco de las páginas públicas (presentación y privacidad). */
export function SiteShell({ children }: { children: React.ReactNode }) {
  const { m } = useI18n();
  const t = m.site;
  return (
    <div className="flex min-h-screen flex-col">
      <header className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-4 py-4">
        <Link href="/welcome" className="flex items-center gap-2 font-semibold">
          <Logo size={28} />
          StayLever
        </Link>
        <div className="flex items-center gap-3 text-sm">
          <LanguageSwitcher />
          <Link href="/login" className="rounded-md bg-primary px-3 py-1.5 text-primary-foreground">
            {t.nav.login}
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 pb-12">{children}</main>
      <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground">
        <Link href="/welcome" className="hover:underline">{t.nav.home}</Link>
        {" · "}
        <Link href="/terms" className="hover:underline">{t.nav.terms}</Link>
        {" · "}
        <Link href="/privacy" className="hover:underline">{t.nav.privacy}</Link>
        {" · "}
        <a href={`mailto:${t.contact}`} className="hover:underline">{t.contact}</a>
      </footer>
    </div>
  );
}
