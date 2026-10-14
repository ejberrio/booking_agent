"use client";

import Link from "next/link";
import { Logo } from "@/components/brand/logo";
import { LanguageSwitcher } from "@/components/i18n/language-switcher";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/lib/i18n";

function SiteLinks() {
  const { m } = useI18n();
  return (
    <div className="mt-4 flex justify-center gap-3 text-[11px] text-muted-foreground">
      <Link href="/welcome" className="hover:underline">StayLever</Link>
      <Link href="/terms" className="hover:underline">{m.site.nav.terms}</Link>
      <Link href="/privacy" className="hover:underline">{m.site.nav.privacy}</Link>
    </div>
  );
}

/** Marco común de las pantallas de acceso (feature 026). */
export function AuthShell({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-8">
      <Card className="w-full max-w-sm">
        <div className="mb-3 flex items-start justify-between">
          <Link href="/login" aria-label="StayLever">
            <Logo size={44} />
          </Link>
          <LanguageSwitcher />
        </div>
        <CardTitle className="text-lg">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        <div className="mt-4">{children}</div>
        {footer && <div className="mt-4 text-center text-xs text-muted-foreground">{footer}</div>}
        <SiteLinks />
      </Card>
    </main>
  );
}

/** Mensaje de error/éxito bajo un formulario. */
export function FormNote({ kind, children }: { kind: "error" | "ok"; children: React.ReactNode }) {
  return (
    <p className={kind === "error" ? "text-xs text-red-500" : "text-xs text-emerald-600"}>
      {children}
    </p>
  );
}

export async function postJson(url: string, body: unknown) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = (await res.json().catch(() => ({}))) as { code?: string; detail?: string };
  return { status: res.status, ok: res.ok, data };
}
