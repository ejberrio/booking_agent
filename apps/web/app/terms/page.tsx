"use client";

import { LegalDoc } from "@/components/legal/legal-doc";
import { SiteShell } from "@/components/site/site-shell";
import { useI18n } from "@/lib/i18n";

// Términos de uso públicos (feature 028): incluyen el encargo del tratamiento de los datos
// de los huéspedes (el anfitrión es Responsable; StayLever, Encargado).
export default function TermsPage() {
  const { m } = useI18n();
  return (
    <SiteShell contact={m.site.privacyContact} back>
      <div className="py-6">
        <LegalDoc kind="terms" />
      </div>
    </SiteShell>
  );
}
