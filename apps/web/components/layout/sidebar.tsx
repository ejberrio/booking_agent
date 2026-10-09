"use client";

import { Logo } from "@/components/brand/logo";
import {
  BadgePercent,
  CalendarDays,
  LayoutDashboard,
  Lightbulb,
  MessageSquare,
  Plug,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { LanguageSwitcher } from "@/components/i18n/language-switcher";
import { useI18n } from "@/lib/i18n";

const NAV = [
  { href: "/", key: "dashboard", icon: LayoutDashboard },
  { href: "/calendar", key: "calendar", icon: CalendarDays },
  { href: "/chat", key: "chat", icon: MessageSquare },
  { href: "/suggestions", key: "suggestions", icon: Lightbulb },
  { href: "/offers", key: "offers", icon: BadgePercent },
  { href: "/onboarding", key: "connection", icon: Plug },
  { href: "/settings", key: "settings", icon: Settings },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const { m } = useI18n();

  async function logout() {
    await fetch("/api/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <>
      <button
        className="fixed left-3 top-3 z-30 rounded-md border border-border bg-card p-2 md:hidden"
        onClick={() => setOpen((v) => !v)}
        aria-label={m.shell.menu}
      >
        ☰
      </button>
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-20 flex w-56 flex-col border-r border-border bg-card p-3 transition-transform md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* En celular el botón ☰ (fijo arriba a la izquierda) tapaba el logo: se deja su hueco. */}
        <div className="mb-4 flex items-center justify-between pl-10 pr-2 md:px-2">
          {/* Logo + nombre → página principal, como en la mayoría de las apps. */}
          <Link
            href="/"
            onClick={() => setOpen(false)}
            aria-label={m.shell.home}
            title={m.shell.home}
            className="flex items-center gap-2 rounded-md text-sm font-semibold hover:opacity-80"
          >
            <Logo size={24} />
            StayLever
          </Link>
          <ThemeToggle />
        </div>
        <nav className="flex-1 space-y-1">
          {NAV.map(({ href, key, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                  active ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                )}
              >
                <Icon size={16} />
                {m.shell.nav[key]}
              </Link>
            );
          })}
        </nav>
        <LanguageSwitcher className="px-3 pt-2" />
        <button
          onClick={logout}
          className="mt-2 rounded-md px-3 py-2 text-left text-xs text-muted-foreground hover:bg-muted"
        >
          {m.shell.logout}
        </button>
      </aside>
    </>
  );
}
