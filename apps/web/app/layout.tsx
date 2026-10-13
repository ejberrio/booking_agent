import type { Metadata } from "next";
import { cookies, headers } from "next/headers";
import "./globals.css";
import { Providers } from "@/components/providers";
import { detectLang, LANG_COOKIE } from "@/lib/i18n/core";

const STAGING_TEXT = {
  es: "AMBIENTE DE PRUEBAS · copia de los datos · nada se publica en Beds24, Booking ni Airbnb",
  en: "TEST ENVIRONMENT · copy of the data · nothing is published to Beds24, Booking or Airbnb",
  pt: "AMBIENTE DE TESTES · cópia dos dados · nada é publicado no Beds24, Booking ou Airbnb",
} as const;

export const metadata: Metadata = {
  title: "StayLever",
  description: "StayLever · precios inteligentes para Booking.com y Airbnb",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // Idioma inicial (feature 021): cookie → navegador → español; así el primer render ya
  // sale en el idioma correcto (sin parpadeo ni desajuste de hidratación).
  const lang = detectLang(
    (await cookies()).get(LANG_COOKIE)?.value,
    (await headers()).get("accept-language"),
  );
  // Ambiente de pruebas (feature 026): STAYLEVER_ENV=staging en la web de pruebas.
  const staging = process.env.STAYLEVER_ENV === "staging";
  return (
    <html lang={lang} suppressHydrationWarning>
      <body>
        {staging && (
          <div className="sticky top-0 z-[60] bg-amber-500 px-3 py-1 text-center text-xs font-semibold text-black">
            {STAGING_TEXT[lang]}
          </div>
        )}
        <Providers initialLang={lang}>{children}</Providers>
      </body>
    </html>
  );
}
