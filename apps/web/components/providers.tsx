"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";
import { Toaster } from "sonner";
import { I18nProvider } from "@/lib/i18n";
import type { Lang } from "@/lib/i18n/core";

export function Providers({
  children,
  initialLang,
}: {
  children: React.ReactNode;
  initialLang: Lang;
}) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
      }),
  );

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <I18nProvider initialLang={initialLang}>
        <QueryClientProvider client={client}>
          {children}
          <Toaster richColors position="top-right" />
        </QueryClientProvider>
      </I18nProvider>
    </ThemeProvider>
  );
}
