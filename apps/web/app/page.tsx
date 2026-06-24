import { ApiStatus } from "@/components/api-status";
import { Chat } from "@/components/chat";

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Booking AI Agent</h1>
          <p className="text-sm text-muted-foreground">
            Gestión inteligente de precios y promociones para Booking.com
          </p>
        </div>
        <ApiStatus />
      </header>

      <Chat />

      <section className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          { t: "Precios por día/rango", d: "Consulta y ajusta tarifas hablando en lenguaje natural." },
          { t: "Sugerencias por eventos", d: "Eventos en Medellín y precios de mercado guían tus tarifas." },
          { t: "LLM configurable", d: "Cambia de modelo según costo o capacidad." },
        ].map((c) => (
          <div key={c.t} className="rounded-xl border border-border bg-card p-4">
            <h3 className="text-sm font-medium">{c.t}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{c.d}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
