"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AuthShell, FormNote, postJson } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { m } = useI18n();
  const t = m.auth;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [code, setCode] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // La cuenta del host original aún sin usuario → configurar el acceso (feature 026).
  useEffect(() => {
    fetch("/api/auth/claim-status")
      .then((r) => r.json())
      .then((d: { claimable?: boolean }) => {
        if (d.claimable) router.replace("/claim");
      })
      .catch(() => null);
  }, [router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setNote(null);
    const { ok, status, data } = await postJson("/api/auth/login", { email, password });
    setLoading(false);
    if (ok) {
      const next = params.get("next");
      router.push(next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
      router.refresh();
      return;
    }
    setCode(data.code ?? null);
    setError(
      status === 429
        ? t.login.tooMany
        : data.code === "email_unverified"
          ? t.login.unverified
          : data.code === "disabled"
            ? t.login.disabled
            : status === 401
              ? t.login.invalid
              : t.login.failed,
    );
  }

  async function resend() {
    await postJson("/api/auth/resend", { email });
    setNote(t.login.resent);
  }

  return (
    <AuthShell
      title={t.login.title}
      footer={<Link href="/forgot" className="underline">{t.login.forgot}</Link>}
    >
      <form onSubmit={onSubmit} className="space-y-3">
        <Input
          type="email"
          autoComplete="email"
          placeholder={t.email}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoFocus
          required
        />
        <Input
          type="password"
          autoComplete="current-password"
          placeholder={t.password}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <FormNote kind="error">{error}</FormNote>}
        {code === "email_unverified" && (
          <button type="button" onClick={resend} className="text-xs underline">
            {t.login.resend}
          </button>
        )}
        {note && <FormNote kind="ok">{note}</FormNote>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? t.login.submitting : t.login.submit}
        </Button>
      </form>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
