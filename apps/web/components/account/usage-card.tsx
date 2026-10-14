"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** Ajustes: mensajes al asistente del mes y búsquedas del escaneo de hoy (feature 027). */
export function UsageCard() {
  const { m, lang } = useI18n();
  const t = m.usage.card;
  const q = useQuery({ queryKey: ["account-usage"], queryFn: api.accountUsage });
  if (!q.data) return null;
  const { chat, search } = q.data;
  const pct = Math.min(100, Math.round((chat.used / Math.max(chat.limit, 1)) * 100));
  const resets = new Date(`${chat.resets_on}T12:00:00`).toLocaleDateString(lang, {
    day: "numeric",
    month: "long",
  });
  const bar = chat.exhausted ? "bg-red-500" : chat.warning ? "bg-amber-500" : "bg-primary";
  return (
    <Card className="space-y-2">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.description}</CardDescription>
      <p className="text-sm font-medium">{t.messages(chat.used, chat.limit)}</p>
      <div className="h-2 w-full overflow-hidden rounded bg-muted">
        <div className={`h-full ${bar}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">
        {chat.exhausted ? m.usage.exhausted(resets) : t.resets(resets)}
      </p>
      <p className="text-xs text-muted-foreground">{t.searches(search.today, search.limit)}</p>
    </Card>
  );
}
