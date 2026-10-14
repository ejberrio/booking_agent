"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AcceptTerms } from "@/components/auth/accept-terms";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

// Feature 028: sin aceptar la versión vigente de Términos y Privacidad la API no responde
// (403 terms_required); esta pantalla lo explica y registra la aceptación.
export function TermsGate() {
  const { m } = useI18n();
  const t = m.legal.gate;
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, staleTime: 5 * 60_000 });
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const onRequired = () => qc.invalidateQueries({ queryKey: ["me"] });
    window.addEventListener("sl:terms-required", onRequired);
    return () => window.removeEventListener("sl:terms-required", onRequired);
  }, [qc]);

  const accept = useMutation({
    mutationFn: () => api.acceptTerms(me.data?.legal_version ?? ""),
    onSuccess: (data) => {
      qc.setQueryData(["me"], data);
      qc.invalidateQueries();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (!me.data?.user.terms_required) return null;

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-background/95 px-4">
      <Card className="w-full max-w-md space-y-3">
        <CardTitle>{t.title}</CardTitle>
        <CardDescription>{t.description}</CardDescription>
        <p className="text-xs text-muted-foreground">
          {t.updated.replace("{date}", me.data.legal_version ?? "")}
        </p>
        <AcceptTerms checked={checked} onChange={setChecked} />
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => accept.mutate()} disabled={!checked || accept.isPending}>
            {t.submit}
          </Button>
          <Button className="bg-muted text-foreground" onClick={logout}>{t.logout}</Button>
        </div>
      </Card>
    </div>
  );
}
