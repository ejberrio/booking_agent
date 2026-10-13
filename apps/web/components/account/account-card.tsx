"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** "Mi cuenta" en Ajustes (feature 026): correo, verificación, contraseña y sesiones. */
export function AccountCard() {
  const { m } = useI18n();
  const t = m.auth.account;
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const [name, setName] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");

  const rename = useMutation({
    mutationFn: (v: string) => api.renameAccount(v),
    onSuccess: () => {
      toast.success(t.nameSaved);
      setName(null);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const renameUser = useMutation({
    mutationFn: (v: string) => api.renameUser(v),
    onSuccess: () => {
      toast.success(t.nameSaved);
      setUserName(null);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const verify = useMutation({
    mutationFn: api.sendVerification,
    onSuccess: (r) => (r.sent ? toast.success(t.verificationSent) : toast.error(t.verificationUnavailable)),
    onError: (e: Error) => toast.error(e.message),
  });
  const pwd = useMutation({
    mutationFn: () => api.changePassword(current, next),
    onSuccess: () => {
      toast.success(t.passwordChanged);
      setCurrent("");
      setNext("");
      setConfirm("");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  async function logoutAll() {
    await api.logoutAll();
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  const u = me.data?.user;
  const account = me.data?.account;
  if (!u || !account) return null;
  return (
    <Card className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <CardTitle>{t.title}</CardTitle>
          <CardDescription>{t.description}</CardDescription>
        </div>
        {u.is_platform_admin && <Badge>{t.admin}</Badge>}
      </div>
      <p className="text-sm">
        {u.email}{" "}
        <Badge variant={u.email_verified ? "success" : "warning"}>
          {u.email_verified ? t.verified : t.unverified}
        </Badge>
      </p>
      {!u.email_verified && (
        <Button className="bg-muted text-foreground" onClick={() => verify.mutate()}
          disabled={verify.isPending}>
          {t.sendVerification}
        </Button>
      )}
      <label className="block space-y-1">
        <span className="text-sm font-medium">{t.yourName}</span>
        <div className="flex gap-2">
          <Input
            value={userName ?? u.name}
            onChange={(e) => setUserName(e.target.value)}
            maxLength={120}
          />
          <Button
            className="shrink-0"
            onClick={() => userName?.trim() && renameUser.mutate(userName.trim())}
            disabled={!userName?.trim() || userName.trim() === u.name || renameUser.isPending}
          >
            {t.saveName}
          </Button>
        </div>
      </label>
      <label className="block space-y-1">
        <span className="text-sm font-medium">{t.accountName}</span>
        <div className="flex gap-2">
          <Input
            value={name ?? account.name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
          />
          <Button
            className="shrink-0"
            onClick={() => name?.trim() && rename.mutate(name.trim())}
            disabled={!name?.trim() || name.trim() === account.name || rename.isPending}
          >
            {t.saveName}
          </Button>
        </div>
        <span className="block text-xs text-muted-foreground">{t.accountNameHint}</span>
      </label>
      <div className="space-y-2">
        <p className="text-sm font-medium">{t.changePassword}</p>
        {u.has_password && (
          <Input type="password" autoComplete="current-password" placeholder={t.currentPassword}
            value={current} onChange={(e) => setCurrent(e.target.value)} />
        )}
        <Input type="password" autoComplete="new-password" placeholder={m.auth.newPassword}
          value={next} onChange={(e) => setNext(e.target.value)} minLength={10} />
        <Input type="password" autoComplete="new-password" placeholder={m.auth.confirmPassword}
          value={confirm} onChange={(e) => setConfirm(e.target.value)} minLength={10} />
        {confirm && confirm !== next && (
          <p className="text-xs text-red-500">{m.auth.mismatch}</p>
        )}
        <Button onClick={() => pwd.mutate()}
          disabled={next.length < 10 || confirm !== next || pwd.isPending}>
          {t.changePassword}
        </Button>
      </div>
      <div className="space-y-1 border-t pt-3">
        <Button className="bg-muted text-foreground" onClick={logoutAll}>{t.logoutAll}</Button>
        <p className="text-xs text-muted-foreground">{t.logoutAllHint}</p>
      </div>
    </Card>
  );
}
