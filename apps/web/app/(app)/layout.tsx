import { FloatingChat } from "@/components/chat/floating-chat";
import { Sidebar } from "@/components/layout/sidebar";
import { ChatProvider } from "@/lib/chat-store";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ChatProvider>
      <div className="min-h-screen">
        <Sidebar />
        <main className="px-4 pb-6 pt-16 md:ml-56 md:px-8 md:pt-6">{children}</main>
      </div>
      {/* Asistente desde cualquier pantalla, con la misma conversación que la sección Chat (feature 024). */}
      <FloatingChat />
    </ChatProvider>
  );
}
