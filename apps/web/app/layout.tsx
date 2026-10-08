import type { Metadata } from "next";
import { cookies, headers } from "next/headers";
import "./globals.css";
import { Providers } from "@/components/providers";
import { detectLang, LANG_COOKIE } from "@/lib/i18n/core";

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
  return (
    <html lang={lang} suppressHydrationWarning>
      <body>
        <Providers initialLang={lang}>{children}</Providers>
      </body>
    </html>
  );
}
