"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { trServer } from "@/lib/i18n/server-messages";
import { streamChat } from "@/lib/sse";

/** Conversación del asistente COMPARTIDA por la sección Chat y el panel flotante (feature 024).
 *
 *  El id de la conversación en curso se recuerda en el navegador y los mensajes se
 *  recuperan del servidor, así la conversación sobrevive a recargas y cambios de sección.
 */

export type ChatMsg = { role: "user" | "agent"; text: string };

interface ChatState {
  messages: ChatMsg[];
  conversationId: number | null;
  pendingActionId: number | null;
  busy: boolean;
  loading: boolean;
  tool: string | null;
  send: (text: string) => Promise<void>;
  newConversation: () => void;
  openConversation: (id: number) => Promise<void>;
}

const STORAGE_KEY = "staylever.chat.conversation";
const ChatContext = createContext<ChatState | null>(null);

function readStoredId(): number | null {
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    return v ? Number(v) || null : null;
  } catch {
    return null;
  }
}

function storeId(id: number | null) {
  try {
    if (id === null) window.localStorage.removeItem(STORAGE_KEY);
    else window.localStorage.setItem(STORAGE_KEY, String(id));
  } catch {
    // almacenamiento no disponible: la conversación sigue en memoria
  }
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const { m } = useI18n();
  const qc = useQueryClient();
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [pendingActionId, setPending] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tool, setTool] = useState<string | null>(null);
  const busyRef = useRef(false);

  const load = useCallback(async (id: number, quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const d = await api.getConversation(id);
      setConversationId(d.id);
      setPending(d.pending_action_id);
      // Las respuestas fijas del servidor se traducen; el texto libre del LLM queda igual.
      setMessages(
        d.messages.map((x) => ({ role: x.role, text: x.role === "agent" ? trServer(x.text) : x.text })),
      );
      storeId(d.id);
    } catch {
      // Conversación inexistente o API caída: se empieza una nueva sin error.
      if (!quiet) {
        setConversationId(null);
        setMessages([]);
        setPending(null);
        storeId(null);
      }
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  // Al montar: retomar la conversación recordada.
  useEffect(() => {
    const id = readStoredId();
    if (id) void load(id);
  }, [load]);

  // Al volver a la pestaña: refrescar (p. ej. se escribió en otra pestaña).
  useEffect(() => {
    const onFocus = () => {
      const id = readStoredId();
      if (id && !busyRef.current) void load(id, true);
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [load]);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || busyRef.current) return;
      setMessages((ms) => [...ms, { role: "user", text }]);
      busyRef.current = true;
      setBusy(true);
      setTool(null);
      try {
        await streamChat(text, conversationId, {
          onTool: (name) => setTool(name),
          onDone: (d) => {
            setConversationId(d.conversation_id);
            storeId(d.conversation_id);
            setPending(d.pending_action_id);
            setMessages((ms) => [...ms, { role: "agent", text: trServer(d.reply) }]);
            // Un cambio aplicado por el asistente se ve en la pantalla de fondo.
            if (d.applied) void qc.invalidateQueries();
          },
        });
      } catch {
        toast.error(m.chat.unreachable);
      } finally {
        busyRef.current = false;
        setBusy(false);
        setTool(null);
      }
    },
    [conversationId, qc, m.chat.unreachable],
  );

  const newConversation = useCallback(() => {
    if (busyRef.current) return;
    setConversationId(null);
    setMessages([]);
    setPending(null);
    storeId(null);
  }, []);

  const openConversation = useCallback(
    async (id: number) => {
      if (busyRef.current) return;
      await load(id);
    },
    [load],
  );

  return (
    <ChatContext.Provider
      value={{
        messages,
        conversationId,
        pendingActionId,
        busy,
        loading,
        tool,
        send,
        newConversation,
        openConversation,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat(): ChatState {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat debe usarse dentro de <ChatProvider>");
  return ctx;
}
