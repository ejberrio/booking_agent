"use client";

import { BadgePercent, ExternalLink, Tag } from "lucide-react";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { EXTERNAL_LINKS } from "@/lib/links";

export default function OffersPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-xl font-semibold">Ofertas</h1>

      <Card>
        <CardTitle>Dos tipos de descuento (no son lo mismo)</CardTitle>
        <div className="mt-3 space-y-3 text-sm">
          <div className="rounded-md border border-border p-3">
            <div className="flex items-center gap-2 font-medium">
              <BadgePercent size={16} className="text-amber-500" /> Ofertas de Booking (visibles)
            </div>
            <p className="mt-1 text-muted-foreground">
              Los <strong>deals con etiqueta/badge</strong> que el huésped ve en tu anuncio
              (Basic Deal, Última hora, Early Booker, Genius). <strong>No se gestionan desde esta
              app</strong>: se crean en el panel de Beds24 o en el extranet de Booking.
            </p>
          </div>
          <div className="rounded-md border border-border p-3">
            <div className="flex items-center gap-2 font-medium">
              <Tag size={16} className="text-primary" /> Promociones de precio internas
            </div>
            <p className="mt-1 text-muted-foreground">
              Solo <strong>bajan el precio publicado</strong> (sin badge). Estas <strong>sí</strong>{" "}
              se gestionan en esta app: pídelas por el{" "}
              <a className="underline" href="/chat">chat</a> (&ldquo;baja el precio 10% en
              septiembre&rdquo;) o en el{" "}
              <a className="underline" href="/calendar">calendario</a>.
            </p>
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>Crear una oferta visible de Booking</CardTitle>
        <CardDescription>
          La API del Channel Manager no permite gestionarlas; se hacen en estos paneles.
        </CardDescription>
        <div className="mt-3 flex flex-wrap gap-2">
          <a
            href={EXTERNAL_LINKS.beds24Dashboard}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground"
          >
            Panel de Beds24 <ExternalLink size={14} />
          </a>
          <a
            href={EXTERNAL_LINKS.bookingExtranet}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm text-foreground"
          >
            Extranet de Booking <ExternalLink size={14} />
          </a>
        </div>
        <ol className="mt-4 list-decimal space-y-1 pl-5 text-xs text-muted-foreground">
          <li>En Beds24: <em>Settings → Channel Manager → Booking.com → Promotions</em>.</li>
          <li>O en el extranet de Booking: <em>Oportunidades / Promociones</em>.</li>
          <li>Elige el tipo (Básica, Última hora, Early Booker), el % y las fechas, y guarda.</li>
          <li>El deal aparecerá con su badge en tu anuncio de Booking.</li>
        </ol>
      </Card>
    </div>
  );
}
