"use client";

import { Send } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { streamChat } from "@/lib/sse";
import { cn } from "@/lib/utils";

type Msg = { role: "user" | "agent"; text: string };

export function ChatPanel() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "agent", text: "Hola 👋 Pregúntame por precios o pídeme cambios; propongo y tú confirmas." },
  ]);
  const [input, setInput] = useState("");
  const [convId, setConvId] = useState<number | null>(null);
  const [pending, setPending] = useState<number | null>(null);
  const [tool, setTool] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    setTool(null);
    try {
      await streamChat(text, convId, {
        onTool: (name) => setTool(name),
        onDone: (d) => {
          setConvId(d.conversation_id);
          setPending(d.pending_action_id);
          setMessages((m) => [...m, { role: "agent", text: d.reply }]);
        },
      });
    } catch {
      toast.error("No pude contactar al agente. ¿Está la API en :8000?");
    } finally {
      setBusy(false);
      setTool(null);
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-xl border border-border bg-card">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((m, i) => (
          <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <div
              className={cn(
                "max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm",
                m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted",
              )}
            >
              {m.text}
            </div>
          </div>
        ))}
        {busy && (
          <div className="text-xs text-muted-foreground">
            {tool ? `Ejecutando: ${tool}…` : "Pensando…"}
          </div>
        )}
        {pending !== null && !busy && (
          <div className="flex gap-2">
            <Button onClick={() => send("sí, confirmo")}>Confirmar</Button>
            <Button className="bg-muted text-foreground" onClick={() => send("no, cancela")}>
              Cancelar
            </Button>
          </div>
        )}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 border-t border-border p-3"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ej: sube 20% los fines de semana de agosto"
          disabled={busy}
        />
        <Button type="submit" disabled={busy}>
          <Send size={16} />
        </Button>
      </form>
    </div>
  );
}
