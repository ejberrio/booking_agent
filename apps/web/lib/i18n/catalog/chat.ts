// Textos del área "chat" (feature 021). El español es la referencia: en/pt deben
// tener EXACTAMENTE las mismas claves (TypeScript falla si falta o sobra alguna).
const es = {
  title: "Chat del agente",
  greeting: "Hola 👋 Pregúntame por precios o pídeme cambios; propongo y tú confirmas.",
  unreachable: "No pude contactar al asistente. Inténtalo de nuevo en un momento.",
  running: (tool: string) => `Ejecutando: ${tool}…`,
  thinking: "Pensando…",
  /** Texto que se envía al agente al pulsar Confirmar / Cancelar (lo interpreta el LLM). */
  confirmMessage: "sí, confirmo",
  cancelMessage: "no, cancela",
  placeholder: "Ej: sube 20% los fines de semana de agosto",
  // --- chat flotante e historial (feature 024) ---
  open: "Abrir asistente",
  close: "Cerrar asistente",
  shortcut: "Ctrl+K / ⌘K",
  newConversation: "Nueva conversación",
  recent: "Recientes",
  noRecent: "Aún no hay conversaciones.",
  current: "actual",
  untitled: "Sin título",
  resize: "Arrastra para cambiar el ancho",
  loading: "Cargando conversación…",
  send: "Enviar",
};

type Shape = typeof es;

const en: Shape = {
  title: "Agent chat",
  greeting: "Hi 👋 Ask me about prices or request changes; I propose and you confirm.",
  unreachable: "Couldn't reach the assistant. Please try again in a moment.",
  running: (tool: string) => `Running: ${tool}…`,
  thinking: "Thinking…",
  confirmMessage: "yes, confirm",
  cancelMessage: "no, cancel",
  placeholder: "E.g. raise August weekends by 20%",
  open: "Open assistant",
  close: "Close assistant",
  shortcut: "Ctrl+K / ⌘K",
  newConversation: "New conversation",
  recent: "Recent",
  noRecent: "No conversations yet.",
  current: "current",
  untitled: "Untitled",
  resize: "Drag to change the width",
  loading: "Loading conversation…",
  send: "Send",
};

const pt: Shape = {
  title: "Chat do agente",
  greeting: "Olá 👋 Pergunte sobre preços ou peça alterações; eu proponho e você confirma.",
  unreachable: "Não consegui falar com o assistente. Tente novamente em instantes.",
  running: (tool: string) => `Executando: ${tool}…`,
  thinking: "Pensando…",
  confirmMessage: "sim, confirmo",
  cancelMessage: "não, cancele",
  placeholder: "Ex.: suba 20% os fins de semana de agosto",
  open: "Abrir assistente",
  close: "Fechar assistente",
  shortcut: "Ctrl+K / ⌘K",
  newConversation: "Nova conversa",
  recent: "Recentes",
  noRecent: "Ainda não há conversas.",
  current: "atual",
  untitled: "Sem título",
  resize: "Arraste para mudar a largura",
  loading: "Carregando conversa…",
  send: "Enviar",
};

const catalog = { es, en, pt };
export default catalog;
