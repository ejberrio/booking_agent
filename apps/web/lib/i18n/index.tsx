"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { isLang, LANG_COOKIE, setActiveLang, type Lang } from "@/lib/i18n/core";
import { MESSAGES, type Messages } from "@/lib/i18n/messages";

interface I18n {
  lang: Lang;
  m: Messages;
  setLang: (lang: Lang) => void;
}

const Ctx = createContext<I18n | null>(null);

function writeCookie(lang: Lang) {
  document.cookie = `${LANG_COOKIE}=${lang}; Path=/; Max-Age=31536000; SameSite=Lax`;
}

/** Idioma de la app (feature 021). `initialLang` llega del servidor (cookie o navegador)
 *  para que el primer render ya esté en el idioma correcto. */
export function I18nProvider({ initialLang, children }: { initialLang: Lang; children: React.ReactNode }) {
  const [lang, setState] = useState<Lang>(() => {
    setActiveLang(initialLang);
    return initialLang;
  });

  const apply = useCallback((next: Lang) => {
    setActiveLang(next);
    setState(next);
    writeCookie(next);
    document.documentElement.lang = next;
  }, []);

  const setLang = useCallback(
    (next: Lang) => {
      apply(next);
      // Preferencia del host para todos sus dispositivos (sin sesión, p. ej. en el
      // login, la petición se redirige y se ignora: queda la cookie).
      fetch("/api/proxy/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: next }),
        redirect: "manual",
      }).catch(() => {});
    },
    [apply],
  );

  // Con sesión, la preferencia guardada en el servidor manda (otro dispositivo).
  useEffect(() => {
    if (window.location.pathname.startsWith("/login")) return;
    fetch("/api/proxy/preferences", { redirect: "manual", cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((p) => {
        if (p && isLang(p.language) && p.language !== initialLang) apply(p.language);
      })
      .catch(() => {});
  }, [apply, initialLang]);

  const value = useMemo(() => ({ lang, m: MESSAGES[lang], setLang }), [lang, setLang]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18n {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useI18n fuera de I18nProvider");
  return ctx;
}
