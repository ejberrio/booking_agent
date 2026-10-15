"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AcceptTerms } from "@/components/auth/accept-terms";
import { AuthShell, FormNote, postJson } from "@/components/auth/auth-shell";
import { GoogleButton, useGoogleError } from "@/components/auth/google-button";
import { REPORT_KEY } from "@/components/site/free-report";
import { WaitlistForm } from "@/components/site/waitlist-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";

// Registro (feature 026, entrega 3): con código de invitación (`?code=` lo rellena) o abierto con
// cupo (feature 030). Lleno el cupo y sin código → lista de espera. `?report=` vincula el informe gratis.
function RegisterForm() {
  const params = useSearchParams();
  const { m, lang } = useI18n();
  const t = m.auth;
  const [open, setOpen] = useState(false);
  const [full, setFull] = useState(params.get("error") === "beta_full");
  const [report, setReport] = useState<string | null>(params.get("report"));
  const [form, setForm] = useState({
    invite_code: params.get("code") ?? "",
    name: "",
    email: "",
    password: "",
  });
  const [confirm, setConfirm] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const googleError = useGoogleError(params.get("error"));
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  useEffect(() => {
    fetch("/api/auth/registration-status")
      .then((r) => r.json())
      .then((d: { open?: boolean; full?: boolean }) => {
        setOpen(Boolean(d.open));
        setFull(Boolean(d.full));
      })
      .catch(() => null);
    if (!params.get("report")) {
      try {
        setReport(sessionStorage.getItem(REPORT_KEY));
      } catch {
        // sin almacenamiento
      }
    }
  }, [params]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password !== confirm) {
      setError(t.mismatch);
      return;
    }
    setLoading(true);
    setError(null);
    const { ok, status, data } = await postJson("/api/auth/register", {
      ...form,
      language: lang,
      accept_terms: accepted,
      report,
    });
    setLoading(false);
    if (ok) {
      setSent(true);
      return;
    }
    if (data.code === "beta_full") {
      setFull(true);
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
      ) : full && !form.invite_code ? (
        <div className="space-y-3">
          <WaitlistForm />
          <button type="button" className="text-xs text-muted-foreground underline"
            onClick={() => setFull(false)}>
            {t.register.haveCode}
          </button>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-3">
          {(!open || form.invite_code) && (
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
          <AcceptTerms checked={accepted} onChange={setAccepted} />
          <Button type="submit" className="w-full" disabled={loading || !accepted}>
            {t.register.submit}
          </Button>
          {googleError && !error && <FormNote kind="error">{googleError}</FormNote>}
          <GoogleButton mode="register" invite={form.invite_code || undefined}
            accepted={accepted} report={report ?? undefined} />
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
