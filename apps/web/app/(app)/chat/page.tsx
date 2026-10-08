"use client";

import { ChatPanel } from "@/components/chat/chat-panel";
import { useI18n } from "@/lib/i18n";

export default function ChatPage() {
  const { m } = useI18n();
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-xl font-semibold">{m.chat.title}</h1>
      <ChatPanel />
    </div>
  );
}
