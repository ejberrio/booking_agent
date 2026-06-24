"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { sendChat } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Message = { role: "user" | "agent"; text: string };

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      text: "Hola 👋 Soy tu asistente de pricing. Pregúntame por precios o pídeme ajustarlos. (Aún es un placeholder: el agente real llega en la Fase 4.)",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const reply = await sendChat(text);
      setMessages((m) => [...m, { role: "agent", text: reply }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "agent", text: `⚠️ No pude contactar la API (${String(err)}). ¿Está corriendo en :8000?` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[28rem] flex-col rounded-xl border border-border bg-card">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
          >
            <div
              className={cn(
                "max-w-[80%] rounded-2xl px-4 py-2 text-sm",
                m.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-foreground",
              )}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && <div className="text-sm text-muted-foreground">Pensando…</div>}
      </div>
      <form onSubmit={onSend} className="flex gap-2 border-t border-border p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ej: ¿Cuánto cuesta el 15 de julio? Sube +20% del 1 al 7 de agosto"
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
        />
        <Button type="submit" disabled={loading}>
          <Send size={16} />
          Enviar
        </Button>
      </form>
    </div>
  );
}
