import { FloatingChat } from "@/components/chat/floating-chat";
import { Sidebar } from "@/components/layout/sidebar";
import { TermsGate } from "@/components/legal/terms-gate";
import { NativeBridge } from "@/components/native/native-bridge";
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
      {/* Solo dentro de la app móvil: botón atrás y avisos (feature 025). */}
      <NativeBridge />
      {/* Términos y Privacidad vigentes sin aceptar → pantalla de aceptación (feature 028). */}
      <TermsGate />
    </ChatProvider>
  );
}
