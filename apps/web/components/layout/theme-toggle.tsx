"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useI18n } from "@/lib/i18n";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  // `resolvedTheme` = el tema que se VE (con "system" puede ser claro u oscuro);
  // usar `theme` hacía que el primer clic eligiera "dark" sobre un sistema ya oscuro.
  const { resolvedTheme, setTheme } = useTheme();
  const { m } = useI18n();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-8 w-8" />;

  return (
    <button
      aria-label={m.shell.toggleTheme}
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      title={m.shell.toggleTheme}
      className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border hover:bg-muted"
    >
      {resolvedTheme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}
