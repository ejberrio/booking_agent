"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AuthShell, FormNote, postJson } from "@/components/auth/auth-shell";
import { GoogleButton, useGoogleError } from "@/components/auth/google-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";

// Registro con código de invitación (feature 026, entrega 3). `?code=` lo rellena.
function RegisterForm() {
  const params = useSearchParams();
  const { m, lang } = useI18n();
  const t = m.auth;
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    invite_code: params.get("code") ?? "",
    name: "",
    email: "",
    password: "",
  });
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const googleError = useGoogleError(params.get("error"));
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  useEffect(() => {
    fetch("/api/auth/registration-status")
      .then((r) => r.json())
      .then((d: { open?: boolean }) => setOpen(Boolean(d.open)))
      .catch(() => null);
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password !== confirm) {
      setError(t.mismatch);
      return;
    }
    setLoading(true);
    setError(null);
    const { ok, status, data } = await postJson("/api/auth/register", { ...form, language: lang });
    setLoading(false);
    if (ok) {
      setSent(true);
      return;
    }
    setError(
      status === 503
        ? t.register.unavailable
        : data.code === "invite_required"
          ? t.register.inviteRequired
          : data.code === "invite_invalid"
            ? t.register.inviteInvalid
            : data.code === "weak_password"
              ? t.weakPassword
              : (data.detail ?? t.login.failed),
    );
  }

  return (
    <AuthShell
      title={t.register.title}
      description={open ? t.register.introOpen : t.register.intro}
      footer={<Link href="/login" className="underline">{t.register.haveAccount}</Link>}
    >
      {sent ? (
        <FormNote kind="ok">{t.register.sent}</FormNote>
      ) : (
        <form onSubmit={onSubmit} className="space-y-3">
          {!open && (
            <Input
              placeholder={t.register.code}
              value={form.invite_code}
              onChange={set("invite_code")}
              autoCapitalize="characters"
              required
            />
          )}
          <Input placeholder={t.name} value={form.name} onChange={set("name")} required />
          <Input type="email" autoComplete="email" placeholder={t.email} value={form.email}
            onChange={set("email")} required />
          <Input type="password" autoComplete="new-password" placeholder={t.newPassword}
            value={form.password} onChange={set("password")} minLength={10} required />
          <Input type="password" autoComplete="new-password" placeholder={t.confirmPassword}
            value={confirm} onChange={(e) => setConfirm(e.target.value)} minLength={10} required />
          <p className="text-xs text-muted-foreground">{t.passwordHint}</p>
          {error && <FormNote kind="error">{error}</FormNote>}
          <Button type="submit" className="w-full" disabled={loading}>
            {t.register.submit}
          </Button>
          {googleError && !error && <FormNote kind="error">{googleError}</FormNote>}
          <GoogleButton mode="register" invite={open ? undefined : form.invite_code} />
        </form>
      )}
    </AuthShell>
  );
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
