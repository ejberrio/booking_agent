"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** "Tus datos" en Ajustes (feature 028): derecho de acceso (copia) y de supresión (borrar). */
export function DataCard() {
  const { m } = useI18n();
  const t = m.legal.data;
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const [exporting, setExporting] = useState(false);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const u = me.data?.user;
  const account = me.data?.account;
  if (!u || !account) return null;
  const isMain = account.id === 1;

  async function download() {
    setExporting(true);
    try {
      const data = await api.exportAccount();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `staylever-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(t.exported);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setExporting(false);
    }
  }

  async function sendCode() {
    try {
      const r = await api.sendDeleteCode();
      if (r.sent) setCodeSent(true);
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function remove() {
    setDeleting(true);
    const res = await fetch("/api/proxy/account/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_name: name,
        password: u?.has_password ? password : undefined,
        code: u?.has_password ? undefined : code,
      }),
    });
    const body = await res.json().catch(() => ({}));
    setDeleting(false);
    if (res.ok) {
      await fetch("/api/auth/logout", { method: "POST" });
      window.location.href = "/welcome";
      return;
    }
    toast.error(
      body.code === "protected"
        ? t.protected
        : body.code === "name_mismatch"
          ? t.nameMismatch
          : t.invalid,
    );
  }

  const ready =
    name.trim() === account.name.trim() &&
    (u.has_password ? password.length > 0 : code.trim().length === 6);

  return (
    <Card className="space-y-3">
      <CardTitle>{t.title}</CardTitle>
      <CardDescription>{t.description}</CardDescription>
      <Button className="bg-muted text-foreground" onClick={download} disabled={exporting}>
        {exporting ? t.exporting : t.export}
      </Button>
      <div className="space-y-2 border-t pt-3">
        <p className="text-sm font-medium text-red-600 dark:text-red-400">{t.deleteTitle}</p>
        {isMain ? (
          <p className="text-xs text-muted-foreground">{t.protected}</p>
        ) : (
          <>
            <p className="text-xs text-muted-foreground">{t.deleteWarning}</p>
            <Input placeholder={t.typeName(account.name)} value={name}
              onChange={(e) => setName(e.target.value)} />
            {u.has_password ? (
              <Input type="password" autoComplete="current-password" placeholder={t.password}
                value={password} onChange={(e) => setPassword(e.target.value)} />
            ) : codeSent ? (
              <>
                <p className="text-xs text-muted-foreground">{t.codeSent}</p>
                <Input inputMode="numeric" maxLength={6} placeholder={t.code} value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
              </>
            ) : (
              <Button className="bg-muted text-foreground" onClick={sendCode}>{t.sendCode}</Button>
            )}
            <Button className="bg-red-600 text-white hover:bg-red-700" onClick={remove}
              disabled={!ready || deleting}>
              {deleting ? t.deleting : t.delete}
            </Button>
          </>
        )}
      </div>
    </Card>
  );
}
