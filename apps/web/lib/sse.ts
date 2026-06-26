import { API_URL } from "@/lib/api";

export interface ChatDoneEvent {
  reply: string;
  conversation_id: number;
  pending_action_id: number | null;
  applied: boolean;
}

export interface StreamHandlers {
  onTool?: (name: string) => void;
  onDone?: (data: ChatDoneEvent) => void;
}

/** Envía un turno al endpoint SSE y procesa los eventos `tool` y `done`. */
export async function streamChat(
  message: string,
  conversationId: number | null,
  handlers: StreamHandlers,
): Promise<void> {
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (!res.body) throw new Error("sin cuerpo de respuesta");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const event = /event:\s*(\w+)/.exec(block)?.[1];
      const dataLine = /data:\s*(.*)/.exec(block)?.[1];
      if (!event || !dataLine) continue;
      if (event === "tool") {
        const d = JSON.parse(dataLine) as { name: string };
        handlers.onTool?.(d.name);
      } else if (event === "done") {
        handlers.onDone?.(JSON.parse(dataLine) as ChatDoneEvent);
      }
    }
  }
}
