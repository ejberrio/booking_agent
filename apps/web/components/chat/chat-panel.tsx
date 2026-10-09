"use client";

import { useQuery } from "@tanstack/react-query";
import { History, MessageSquarePlus, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useChat } from "@/lib/chat-store";
import { dateTime } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/** Chat del asistente. Lo usan la sección Chat y el panel flotante con el MISMO estado (feature 024). */
export function ChatPanel({ compact = false }: { compact?: boolean }) {
  const { m: msgs } = useI18n();
  const t = msgs.chat;
  const chat = useChat();
  const [input, setInput] = useState("");
  const [showRecent, setShowRecent] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const recent = useQuery({
    queryKey: ["chat-conversations"],
    queryFn: () => api.listConversations(20),
    enabled: showRecent,
    staleTime: 0,
  });

  // Siempre mostrar lo último.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [chat.messages.length, chat.busy]);

  async function send(text: string) {
    if (!text.trim() || chat.busy) return;
    setInput("");
    await chat.send(text);
  }

  return (
    <div
      className={cn(
        "flex flex-col bg-card",
        compact ? "h-full" : "h-[calc(100vh-8rem)] rounded-xl border border-border",
      )}
    >
      <div className="flex items-center justify-end gap-1 border-b border-border px-3 py-2">
        <button
          type="button"
          onClick={() => setShowRecent((v) => !v)}
          className={cn(
            "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted",
            showRecent && "bg-muted text-foreground",
          )}
          aria-expanded={showRecent}
        >
          <History size={14} /> {t.recent}
        </button>
        <button
          type="button"
          onClick={() => {
            chat.newConversation();
            setShowRecent(false);
          }}
          disabled={chat.busy}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted disabled:opacity-50"
        >
          <MessageSquarePlus size={14} /> {t.newConversation}
        </button>
      </div>

      {showRecent && (
        <div className="max-h-64 overflow-y-auto border-b border-border p-2">
          {recent.isLoading ? (
            <p className="px-2 py-1 text-xs text-muted-foreground">{t.loading}</p>
          ) : (recent.data ?? []).length === 0 ? (
            <p className="px-2 py-1 text-xs text-muted-foreground">{t.noRecent}</p>
          ) : (
            <ul className="space-y-0.5">
              {(recent.data ?? []).map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    disabled={chat.busy}
                    onClick={async () => {
                      await chat.openConversation(c.id);
                      setShowRecent(false);
                    }}
                    className={cn(
                      "flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-muted",
                      c.id === chat.conversationId && "bg-muted",
                    )}
                  >
                    <span className="truncate">
                      {c.title || t.untitled}
                      {c.id === chat.conversationId && (
                        <span className="ml-1 text-[10px] text-muted-foreground">· {t.current}</span>
                      )}
                    </span>
                    <span className="shrink-0 text-[10px] text-muted-foreground">{dateTime(c.updated_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {chat.loading ? (
          <p className="text-xs text-muted-foreground">{t.loading}</p>
        ) : (
          [{ role: "agent" as const, text: t.greeting }, ...chat.messages].map((m, i) => (
            <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
              <div
                className={cn(
                  "whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm",
                  compact ? "max-w-[90%]" : "max-w-[80%]",
                  m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted",
                )}
              >
                {m.text}
              </div>
            </div>
          ))
        )}
        {chat.busy && (
          <div className="text-xs text-muted-foreground">
            {chat.tool ? t.running(chat.tool) : t.thinking}
          </div>
        )}
        {chat.pendingActionId !== null && !chat.busy && (
          <div className="flex gap-2">
            <Button onClick={() => send(t.confirmMessage)}>{msgs.common.confirm}</Button>
            <Button className="bg-muted text-foreground" onClick={() => send(t.cancelMessage)}>
              {msgs.common.cancel}
            </Button>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send(input);
        }}
        className="flex gap-2 border-t border-border p-3"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t.placeholder}
          disabled={chat.busy}
          autoFocus={compact}
        />
        <Button type="submit" disabled={chat.busy} aria-label={t.send} title={t.send}>
          <Send size={16} />
        </Button>
      </form>
    </div>
  );
}
