"use client";

import { CalendarDays, LayoutDashboard, Lightbulb, MessageSquare, Plug, Settings } from "lucide-react";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/theme-toggle";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/calendar", label: "Calendario", icon: CalendarDays },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/suggestions", label: "Sugerencias", icon: Lightbulb },
  { href: "/onboarding", label: "Conexión", icon: Plug },
  { href: "/settings", label: "Configuración", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

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
        aria-label="Menú"
      >
        ☰
      </button>
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-20 flex w-56 flex-col border-r border-border bg-card p-3 transition-transform md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="mb-4 flex items-center justify-between px-2">
          <span className="text-sm font-semibold">Booking AI</span>
          <ThemeToggle />
        </div>
        <nav className="flex-1 space-y-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <a
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                  active ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                )}
              >
                <Icon size={16} />
                {label}
              </a>
            );
          })}
        </nav>
        <button
          onClick={logout}
          className="mt-2 rounded-md px-3 py-2 text-left text-xs text-muted-foreground hover:bg-muted"
        >
          Cerrar sesión
        </button>
      </aside>
    </>
  );
}
