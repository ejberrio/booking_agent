"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AuthShell, FormNote, postJson } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";

function ResetForm() {
  const token = useSearchParams().get("token") ?? "";
  const { m } = useI18n();
  const t = m.auth;
  const [password, setPassword] = useState("");
  const [state, setState] = useState<"form" | "done">("form");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const { ok, data } = await postJson("/api/auth/reset", { token, password });
    setLoading(false);
    if (ok) setState("done");
    else setError(data.code === "weak_password" ? t.weakPassword : t.reset.invalid);
  }

  return (
    <AuthShell
      title={t.reset.title}
      footer={<Link href="/login" className="underline">{t.forgot.back}</Link>}
    >
      {state === "done" ? (
        <FormNote kind="ok">{t.reset.done}</FormNote>
      ) : (
        <form onSubmit={onSubmit} className="space-y-3">
          <Input
            type="password"
            autoComplete="new-password"
            placeholder={t.newPassword}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={10}
            autoFocus
            required
          />
          <p className="text-xs text-muted-foreground">{t.passwordHint}</p>
          {error && <FormNote kind="error">{error}</FormNote>}
          <Button type="submit" className="w-full" disabled={loading}>
            {t.reset.submit}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}

export default function ResetPage() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}
