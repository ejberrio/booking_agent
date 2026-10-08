"use client";

import { useRouter } from "next/navigation";
import { Logo } from "@/components/brand/logo";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LanguageSwitcher } from "@/components/i18n/language-switcher";
import { useI18n } from "@/lib/i18n";

export default function LoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { m } = useI18n();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    setLoading(false);
    if (res.ok) {
      router.push("/");
      router.refresh();
    } else {
      setError(res.status === 401 ? m.shell.login.wrongPassword : m.shell.login.failed);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <div className="mb-3 flex items-start justify-between">
          <Logo size={44} />
          <LanguageSwitcher />
        </div>
        <CardTitle className="text-lg">StayLever</CardTitle>
        <CardDescription>{m.shell.login.subtitle}</CardDescription>
        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <Input
            type="password"
            placeholder={m.shell.login.password}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
          />
          {error && <p className="text-xs text-red-500">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? m.shell.login.submitting : m.shell.login.submit}
          </Button>
        </form>
      </Card>
    </main>
  );
}
