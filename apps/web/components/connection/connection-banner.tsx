"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

/** Feature 044: aviso fijo cuando Beds24 dejó de aceptar la conexión, con «Reconectar». */
export function ConnectionBanner() {
  const { m } = useI18n();
  const path = usePathname();
  const q = useQuery({ queryKey: ["connection"], queryFn: api.connection, staleTime: 5 * 60_000, retry: false });
  if (!q.data || q.data.mode === "manual" || q.data.status !== "invalid" || path.startsWith("/onboarding")) {
    return null;
  }
  return (
    <div role="alert" className="mb-4 flex flex-wrap items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm">
      <span className="flex-1">{m.connection.banner.lost}</span>
      <Link href="/onboarding" className="rounded-md bg-amber-600 px-3 py-1 text-xs font-medium text-white">
        {m.connection.banner.reconnect}
      </Link>
    </div>
  );
}
