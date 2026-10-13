"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthShell, FormNote, postJson } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";

// Reclamar la cuenta del host original (feature 026): contraseña de siempre + usuario nuevo.
export default function ClaimPage() {
  const router = useRouter();
  const { m, lang } = useI18n();
  const t = m.auth;
  const [form, setForm] = useState({ app_password: "", name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const { ok, data } = await postJson("/api/auth/claim", { ...form, language: lang });
    setLoading(false);
    if (ok) {
      router.push("/");
      router.refresh();
      return;
    }
    setError(
      data.code === "wrong_app_password"
        ? t.claim.wrongAppPassword
        : data.code === "weak_password"
          ? t.weakPassword
          : data.code === "email_taken"
            ? t.emailTaken
            : data.code === "already_claimed"
              ? t.claim.already
              : (data.detail ?? t.login.failed),
    );
  }

  return (
    <AuthShell title={t.claim.title} description={t.claim.intro}>
      <form onSubmit={onSubmit} className="space-y-3">
        <Input
          type="password"
          autoComplete="current-password"
          placeholder={t.claim.appPassword}
          value={form.app_password}
          onChange={set("app_password")}
          autoFocus
          required
        />
        <Input placeholder={t.name} value={form.name} onChange={set("name")} required />
        <Input
          type="email"
          autoComplete="email"
          placeholder={t.email}
          value={form.email}
          onChange={set("email")}
          required
        />
        <Input
          type="password"
          autoComplete="new-password"
          placeholder={t.newPassword}
          value={form.password}
          onChange={set("password")}
          minLength={10}
          required
        />
        <p className="text-xs text-muted-foreground">{t.passwordHint}</p>
        {error && <FormNote kind="error">{error}</FormNote>}
        <Button type="submit" className="w-full" disabled={loading}>
          {t.claim.submit}
        </Button>
      </form>
    </AuthShell>
  );
}
