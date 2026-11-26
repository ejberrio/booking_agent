"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/brand/logo";
import { LanguageSwitcher } from "@/components/i18n/language-switcher";
import { GuestForm, emptyGuests } from "@/components/registration/guest-form";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { dateWithYear } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { CheckinInfo, GuestData } from "@/lib/types";

// Enlace público de registro del huésped (feature 046). Sin sesión: va por /api/public/checkin/{token}.
// Nunca muestra datos guardados (ni el nombre de la reserva): solo alojamiento y fechas.
export default function CheckinPage() {
  const { token } = useParams<{ token: string }>();
  const { m, lang } = useI18n();
  const t = m.registration.guest;
  const [info, setInfo] = useState<CheckinInfo | null | "closed">(null);
  const [data, setData] = useState<GuestData>(emptyGuests);
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState<Record<string, string[]> | undefined>();
  const [state, setState] = useState<"idle" | "sending" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/public/checkin/${token}`, { cache: "no-store" })
      .then(async (r) => (r.ok ? setInfo(await r.json()) : setInfo("closed")))
      .catch(() => setInfo("closed"));
  }, [token]);

  async function submit() {
    setState("sending");
    setError(null);
    try {
      const r = await fetch(`/api/public/checkin/${token}`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ data, consent }),
      });
      const body = await r.json().catch(() => null);
      if (r.ok) {
        setState("done");
        window.scrollTo({ top: 0 });
        return;
      }
      setErrors(body?.fields);
      setError(body?.code === "invalid" ? t.fix : body?.code === "not_found" ? t.closed : body?.detail ?? t.fix);
    } catch {
      setError(t.fix);
    }
    setState("idle");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="mx-auto flex w-full max-w-2xl items-center justify-between px-4 py-4">
        <span className="flex items-center gap-2 font-semibold"><Logo size={24} /> StayLever</span>
        <LanguageSwitcher />
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 space-y-4 px-4 pb-12">
        <h1 className="text-xl font-semibold">{t.title}</h1>
        {info === null && <Skeleton className="h-64" />}
        {info === "closed" && <Card><p className="text-sm">{t.closed}</p></Card>}
        {info && info !== "closed" && state === "done" && <Card><p className="text-sm">{t.done}</p></Card>}
        {info && info !== "closed" && state !== "done" && (
          <>
            <p className="text-sm font-medium">
              {t.stay([info.unit, info.city].filter(Boolean).join(", "), dateWithYear(info.check_in, lang),
                dateWithYear(info.check_out, lang))}
            </p>
            <p className="text-sm text-muted-foreground">{t.intro}</p>
            {info.submitted && <p className="rounded-md bg-emerald-500/10 p-2 text-sm text-emerald-700 dark:text-emerald-400">{t.already}</p>}
            <GuestForm value={data} onChange={setData} errors={errors} />
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>
                {t.consent}{" "}
                <Link href="/privacy" target="_blank" className="text-primary underline">{t.privacy}</Link>
              </span>
            </label>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button onClick={submit} disabled={!consent || state === "sending"} className="w-full sm:w-auto">
              {state === "sending" ? t.submitting : t.submit}
            </Button>
          </>
        )}
      </main>
    </div>
  );
}
