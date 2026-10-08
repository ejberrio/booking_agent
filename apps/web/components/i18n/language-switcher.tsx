"use client";

import { Languages } from "lucide-react";
import { LANG_LABEL, LANGS, type Lang } from "@/lib/i18n/core";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/** Selector de idioma (feature 021): cada idioma con su nombre en su propio idioma. */
export function LanguageSwitcher({ className }: { className?: string }) {
  const { lang, setLang, m } = useI18n();
  return (
    <label className={cn("flex items-center gap-2 text-xs text-muted-foreground", className)}>
      <Languages size={14} aria-hidden="true" />
      <span className="sr-only">{m.common.language}</span>
      <select
        value={lang}
        onChange={(e) => setLang(e.target.value as Lang)}
        className="rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground"
        aria-label={m.common.language}
      >
        {LANGS.map((l) => (
          <option key={l} value={l}>
            {LANG_LABEL[l]}
          </option>
        ))}
      </select>
    </label>
  );
}
