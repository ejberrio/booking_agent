import calendar from "@/lib/i18n/catalog/calendar";
import chat from "@/lib/i18n/catalog/chat";
import common from "@/lib/i18n/catalog/common";
import connection from "@/lib/i18n/catalog/connection";
import dashboard from "@/lib/i18n/catalog/dashboard";
import offers from "@/lib/i18n/catalog/offers";
import rationale from "@/lib/i18n/catalog/rationale";
import settings from "@/lib/i18n/catalog/settings";
import shell from "@/lib/i18n/catalog/shell";
import suggestions from "@/lib/i18n/catalog/suggestions";
import type { Lang } from "@/lib/i18n/core";

// Compone los catálogos por área en un objeto por idioma (feature 021).
const AREAS = {
  common,
  shell,
  dashboard,
  calendar,
  chat,
  suggestions,
  rationale,
  offers,
  connection,
  settings,
};

type Areas = typeof AREAS;
export type Messages = { [K in keyof Areas]: Areas[K]["es"] };

function forLang(lang: Lang): Messages {
  return Object.fromEntries(
    Object.entries(AREAS).map(([k, c]) => [k, c[lang]]),
  ) as Messages;
}

export const MESSAGES: Record<Lang, Messages> = { es: forLang("es"), en: forLang("en"), pt: forLang("pt") };
