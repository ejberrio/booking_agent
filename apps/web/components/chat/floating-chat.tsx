"use client";

import { Bot, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatPanel } from "@/components/chat/chat-panel";
import { useChat } from "@/lib/chat-store";
import { useI18n } from "@/lib/i18n";

const WIDTH_KEY = "staylever.chat.width";
const MIN_W = 360;
const MAX_W = 720;
const DEFAULT_W = 420;

function readWidth(): number {
  try {
    const v = Number(window.localStorage.getItem(WIDTH_KEY));
    return v >= MIN_W && v <= MAX_W ? v : DEFAULT_W;
  } catch {
    return DEFAULT_W;
  }
}

/** Botón flotante + panel lateral del asistente desde cualquier pantalla (feature 024).
 *  Superpuesto a la derecha SIN oscurecer la página; pantalla completa en celular.
 *  Ctrl+K / ⌘K alterna, Esc cierra; el ancho se arrastra (360–720 px) y se recuerda. */
export function FloatingChat() {
  const { m } = useI18n();
  const t = m.chat;
  const pathname = usePathname();
  const { busy } = useChat();
  const [open, setOpen] = useState(false);
  const [width, setWidth] = useState(DEFAULT_W);
  const dragging = useRef(false);
  const widthRef = useRef(DEFAULT_W);
  const onChatPage = pathname?.startsWith("/chat") ?? false;

  useEffect(() => {
    widthRef.current = readWidth();
    setWidth(widthRef.current);
  }, []);

  // En la sección Chat el chat ya está en pantalla: el panel no aplica.
  useEffect(() => {
    if (onChatPage) setOpen(false);
  }, [onChatPage]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        if (onChatPage) return;
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onChatPage]);

  const onPointerMove = useCallback((e: PointerEvent) => {
    if (!dragging.current) return;
    const w = Math.min(MAX_W, Math.max(MIN_W, window.innerWidth - e.clientX));
    widthRef.current = w;
    setWidth(w);
  }, []);

  const stopDrag = useCallback(() => {
    if (!dragging.current) return;
    dragging.current = false;
    document.body.style.userSelect = "";
    try {
      window.localStorage.setItem(WIDTH_KEY, String(widthRef.current));
    } catch {
      // sin almacenamiento: el ancho vale solo para esta visita
    }
  }, []);

  useEffect(() => {
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopDrag);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopDrag);
    };
  }, [onPointerMove, stopDrag]);

  if (onChatPage) return null;

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          title={`${t.open} (${t.shortcut})`}
          aria-label={t.open}
          className="fixed bottom-5 right-5 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition hover:scale-105 hover:opacity-95"
        >
          <Bot size={22} />
          {busy && (
            <span className="absolute right-1 top-1 h-2.5 w-2.5 animate-pulse rounded-full bg-amber-400" />
          )}
        </button>
      )}

      {open && (
        <aside
          role="dialog"
          aria-label={t.title}
          className="fixed inset-0 z-40 flex flex-col border-l border-border bg-card shadow-2xl md:inset-y-0 md:left-auto md:right-0 md:w-[var(--chat-w)]"
          style={{ ["--chat-w" as string]: `${width}px` }}
        >
          {/* Asa para cambiar el ancho (solo escritorio). */}
          <div
            role="separator"
            aria-orientation="vertical"
            title={t.resize}
            onPointerDown={(e) => {
              e.preventDefault();
              dragging.current = true;
              document.body.style.userSelect = "none";
            }}
            className="absolute inset-y-0 -left-1 hidden w-2 cursor-col-resize hover:bg-primary/30 md:block"
          />
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2">
              <Bot size={18} className="text-primary" />
              <span className="text-sm font-semibold">{t.title}</span>
              <span className="hidden rounded border border-border px-1.5 text-[10px] text-muted-foreground md:inline">
                {t.shortcut}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label={t.close}
              title={t.close}
              className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X size={18} />
            </button>
          </div>
          <div className="min-h-0 flex-1">
            <ChatPanel compact />
          </div>
        </aside>
      )}
    </>
  );
}
