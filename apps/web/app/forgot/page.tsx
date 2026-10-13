"use client";

import Link from "next/link";
import { useState } from "react";
import { AuthShell, FormNote, postJson } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/lib/i18n";

export default function ForgotPage() {
  const { m, lang } = useI18n();
  const t = m.auth;
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    await postJson("/api/auth/forgot", { email, language: lang });
    setLoading(false);
    setSent(true); // misma respuesta exista o no el correo
  }

  return (
    <AuthShell
      title={t.forgot.title}
      description={t.forgot.intro}
      footer={<Link href="/login" className="underline">{t.forgot.back}</Link>}
    >
      {sent ? (
        <FormNote kind="ok">{t.forgot.sent}</FormNote>
      ) : (
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
          <Button type="submit" className="w-full" disabled={loading}>
            {t.forgot.submit}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
