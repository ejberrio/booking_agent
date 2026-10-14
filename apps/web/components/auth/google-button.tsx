"use client";

import { useEffect, useState } from "react";
import { FormNote } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";
import { appVersion, isNativeApp } from "@/lib/native";

// Entrar con Google (feature 026, entrega 4). En el navegador va directo a Google. En la app de
// Android Google no deja entrar dentro del WebView: se abre en el navegador del sistema y vuelve
// a la app por `com.staylever.app://auth` con un código de traspaso que solo sirve con el
// verificador guardado aquí (PKCE). Requiere la app 1.1.0 o superior.
const VERIFIER_KEY = "sl_google_verifier";
const APP_MIN = [1, 1, 0];

function supportsGoogle(version: string | undefined): boolean {
  if (!version) return false;
  const v = version.split(".").map((n) => parseInt(n, 10) || 0);
  for (let i = 0; i < 3; i++) {
    if ((v[i] ?? 0) !== APP_MIN[i]) return (v[i] ?? 0) > APP_MIN[i];
  }
  return true;
}

function b64url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function pkcePair(): Promise<{ verifier: string; challenge: string }> {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(48)));
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return { verifier, challenge: b64url(new Uint8Array(hash)) };
}

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true" className="mr-2">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

export function GoogleButton({
  mode,
  invite,
  accepted,
  report,
}: {
  mode: "login" | "register";
  invite?: string;
  /** Informe gratis (feature 030) que se vincula a la cuenta nueva. */
  report?: string;
  /** Registro: la casilla de Términos y Privacidad (feature 028) debe estar marcada. */
  accepted?: boolean;
}) {
  const { m, lang } = useI18n();
  const t = m.auth.google;
  const [available, setAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const native = typeof window !== "undefined" && isNativeApp();
  const nativeOk = native && supportsGoogle(appVersion());

  useEffect(() => {
    fetch("/api/auth/providers")
      .then((r) => r.json())
      .then((d: { google?: boolean }) => setAvailable(Boolean(d.google)))
      .catch(() => null);
  }, []);

  // App: al volver de Google, Android abre com.staylever.app://auth?code=… → sesión.
  useEffect(() => {
    if (!nativeOk) return;
    let remove: (() => void) | undefined;
    (async () => {
      const { App } = await import("@capacitor/app");
      const { Browser } = await import("@capacitor/browser");
      const h = await App.addListener("appUrlOpen", ({ url }) => {
        if (!url.startsWith("com.staylever.app://auth")) return;
        void Browser.close().catch(() => undefined);
        const code = new URL(url.replace("com.staylever.app://", "https://app/")).searchParams.get("code");
        let verifier = "";
        try {
          verifier = localStorage.getItem(VERIFIER_KEY) ?? "";
          localStorage.removeItem(VERIFIER_KEY);
        } catch {
          // sin almacenamiento: el canje fallará y se mostrará el error
        }
        if (!code) return;
        const qs = new URLSearchParams({ code, verifier });
        window.location.assign(`/api/auth/handoff?${qs}`);
      });
      remove = () => void h.remove();
    })().catch(() => undefined);
    return () => remove?.();
  }, [nativeOk]);

  if (!available) return null;
  if (native && !nativeOk) return <FormNote kind="error">{t.updateApp}</FormNote>;

  async function go() {
    setBusy(true);
    const qs = new URLSearchParams({ mode, lang });
    if (invite?.trim()) qs.set("invite", invite.trim());
    if (accepted) qs.set("accept", "1");
    if (report) qs.set("report", report);
    if (!nativeOk) {
      window.location.assign(`/api/auth/google/start?${qs}`);
      return;
    }
    try {
      const { verifier, challenge } = await pkcePair();
      localStorage.setItem(VERIFIER_KEY, verifier);
      qs.set("client", "app");
      qs.set("challenge", challenge);
      const { Browser } = await import("@capacitor/browser");
      await Browser.open({ url: `${window.location.origin}/api/auth/google/start?${qs}` });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        {t.or}
        <span className="h-px flex-1 bg-border" />
      </div>
      <Button type="button" onClick={go} disabled={busy || (mode === "register" && !accepted)}
        className="w-full border border-border bg-background text-foreground hover:bg-muted">
        <GoogleMark />
        {mode === "register" ? t.register : t.login}
      </Button>
    </div>
  );
}

/** Mensaje para `?error=` que deja el regreso de Google en /login o /register. */
export function useGoogleError(code: string | null): string | null {
  const { m } = useI18n();
  if (!code) return null;
  const e = m.auth.google.errors as Record<string, string>;
  return e[code] ?? e.google_failed;
}
