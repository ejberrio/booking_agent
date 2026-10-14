"use client";

import { useState } from "react";
import { FormNote } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";

/** Lista de espera de la beta (feature 030): correo + autorización explícita (Ley 1581). */
export function WaitlistForm({ municipalityCode }: { municipalityCode?: string }) {
  const { m, lang } = useI18n();
  const t = m.pub.waitlist;
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [state, setState] = useState<"idle" | "busy" | "done" | "error">("idle");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setState("busy");
    const r = await fetch("/api/public/waitlist", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, consent, language: lang, municipality_code: municipalityCode }),
    }).catch(() => null);
    setState(r?.ok ? "done" : "error");
  }

  if (state === "done") return <FormNote kind="ok">{t.done}</FormNote>;
  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <h3 className="font-medium">{t.title}</h3>
        <p className="text-sm text-muted-foreground">{t.text}</p>
      </div>
      <Input type="email" autoComplete="email" placeholder={t.email} value={email}
        onChange={(e) => setEmail(e.target.value)} required />
      <label className="flex items-start gap-2 text-xs text-muted-foreground">
        <input type="checkbox" className="mt-0.5" checked={consent}
          onChange={(e) => setConsent(e.target.checked)} />
        <span>{t.consent}</span>
      </label>
      {state === "error" && <FormNote kind="error">{t.error}</FormNote>}
      <Button type="submit" className="w-full" disabled={!consent || state === "busy"}>
        {t.submit}
      </Button>
    </form>
  );
}
