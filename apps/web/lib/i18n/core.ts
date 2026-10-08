/** Núcleo de idioma (feature 021): idiomas soportados, locale de formatos y el idioma
 *  ACTIVO a nivel de módulo, para que formatos y `req()` lo usen sin prop-drilling. */

export type Lang = "es" | "en" | "pt";
export const LANGS: Lang[] = ["es", "en", "pt"];
export const LANG_LABEL: Record<Lang, string> = { es: "Español", en: "English", pt: "Português" };
/** Variantes confirmadas por el host: inglés de EE. UU. y portugués de Brasil. */
export const LOCALE: Record<Lang, string> = { es: "es-CO", en: "en-US", pt: "pt-BR" };
export const LANG_COOKIE = "lang";

let active: Lang = "es";

export function getActiveLang(): Lang {
  return active;
}

export function setActiveLang(lang: Lang): void {
  active = lang;
}

export function isLang(v: unknown): v is Lang {
  return v === "es" || v === "en" || v === "pt";
}

/** Cookie válida → esa; si no, primer idioma soportado del navegador (cualquier variante); si no, es. */
export function detectLang(cookie: string | undefined, acceptLanguage: string | null | undefined): Lang {
  if (isLang(cookie)) return cookie;
  for (const part of (acceptLanguage ?? "").split(",")) {
    const base = part.trim().slice(0, 2).toLowerCase();
    if (isLang(base)) return base;
  }
  return "es";
}
