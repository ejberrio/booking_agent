"use client";

import { LegalDoc } from "@/components/legal/legal-doc";
import { SiteShell } from "@/components/site/site-shell";
import { useI18n } from "@/lib/i18n";

// Política de privacidad pública (features 026 y 028; Google la exige para "Entrar con Google").
export default function PrivacyPage() {
  const { m } = useI18n();
  return (
    <SiteShell contact={m.site.privacyContact} back>
      <div className="py-6">
        <LegalDoc kind="privacy" />
      </div>
    </SiteShell>
  );
}
