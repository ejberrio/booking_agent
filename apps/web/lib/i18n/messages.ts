import account from "@/lib/i18n/catalog/account";
import admin from "@/lib/i18n/catalog/admin";
import auth from "@/lib/i18n/catalog/auth";
import calendar from "@/lib/i18n/catalog/calendar";
import chat from "@/lib/i18n/catalog/chat";
import common from "@/lib/i18n/catalog/common";
import connection from "@/lib/i18n/catalog/connection";
import dashboard from "@/lib/i18n/catalog/dashboard";
import extension from "@/lib/i18n/catalog/extension";
import legal from "@/lib/i18n/catalog/legal";
import offers from "@/lib/i18n/catalog/offers";
import offline from "@/lib/i18n/catalog/offline";
import rationale from "@/lib/i18n/catalog/rationale";
import settings from "@/lib/i18n/catalog/settings";
import shell from "@/lib/i18n/catalog/shell";
import site from "@/lib/i18n/catalog/site";
import suggestions from "@/lib/i18n/catalog/suggestions";
import terms from "@/lib/i18n/catalog/terms";
import usage from "@/lib/i18n/catalog/usage";
import type { Lang } from "@/lib/i18n/core";

// Compone los catálogos por área en un objeto por idioma (feature 021).
const AREAS = {
  common,
  account,
  admin,
  auth,
  legal,
  shell,
  site,
  terms,
  usage,
  dashboard,
  calendar,
  extension,
  chat,
  suggestions,
  rationale,
  offers,
  offline,
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
