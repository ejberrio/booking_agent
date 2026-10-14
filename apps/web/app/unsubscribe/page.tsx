"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { FormNote } from "@/components/auth/auth-shell";
import { SiteShell } from "@/components/site/site-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useI18n } from "@/lib/i18n";

// Apagar el resumen semanal desde el enlace firmado del correo (feature 030). Pide confirmar con
// un botón: los lectores de correo que abren enlaces solos no lo apagan por error.
function Unsubscribe() {
  const params = useSearchParams();
  const { m } = useI18n();
  const t = m.pub.digest;
  const [state, setState] = useState<"ask" | "busy" | "done" | "error">("ask");

  async function confirm() {
    setState("busy");
    const r = await fetch("/api/public/unsubscribe", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ u: Number(params.get("u")) || 0, t: params.get("t") ?? "" }),
    }).catch(() => null);
    setState(r?.ok ? "done" : "error");
  }

  return (
    <Card className="mx-auto mt-8 max-w-md space-y-3">
      <h1 className="text-lg font-semibold">{t.unsubTitle}</h1>
      {state === "done" ? (
        <FormNote kind="ok">{t.unsubDone}</FormNote>
      ) : state === "error" ? (
        <FormNote kind="error">{t.unsubError}</FormNote>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">{t.unsubAsk}</p>
          <Button onClick={confirm} disabled={state === "busy"}>{t.unsubCta}</Button>
        </>
      )}
    </Card>
  );
}

export default function UnsubscribePage() {
  return (
    <SiteShell>
      <Suspense>
        <Unsubscribe />
      </Suspense>
    </SiteShell>
  );
}
