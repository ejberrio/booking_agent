"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { AuthShell, FormNote, postJson } from "@/components/auth/auth-shell";
import { useI18n } from "@/lib/i18n";

function Verify() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const { m } = useI18n();
  const t = m.auth.verify;
  const [state, setState] = useState<"working" | "ok" | "already" | "invalid">("working");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // el enlace es de un solo uso: una sola llamada
    started.current = true;
    postJson("/api/auth/verify", { token }).then(({ ok, data }) => {
      setState(ok ? "ok" : data.code === "already_verified" ? "already" : "invalid");
      if (ok) setTimeout(() => router.replace("/"), 1200);
    });
  }, [token, router]);

  return (
    <AuthShell title={state === "ok" ? t.ok : state === "already" ? t.already : t.title}>
      {state === "invalid" && <FormNote kind="error">{t.invalid}</FormNote>}
      {state === "already" && (
        <Link href="/" className="text-sm underline">
          {t.goHome}
        </Link>
      )}
    </AuthShell>
  );
}

export default function VerifyPage() {
  return (
    <Suspense>
      <Verify />
    </Suspense>
  );
}
