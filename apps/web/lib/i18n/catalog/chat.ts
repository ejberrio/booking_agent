// Textos del área "chat" (feature 021). El español es la referencia: en/pt deben
// tener EXACTAMENTE las mismas claves (TypeScript falla si falta o sobra alguna).
const es = {
  title: "Chat del agente",
  greeting: "Hola 👋 Pregúntame por precios o pídeme cambios; propongo y tú confirmas.",
  unreachable: "No pude contactar al agente. ¿Está la API en :8000?",
  running: (tool: string) => `Ejecutando: ${tool}…`,
  thinking: "Pensando…",
  /** Texto que se envía al agente al pulsar Confirmar / Cancelar (lo interpreta el LLM). */
  confirmMessage: "sí, confirmo",
  cancelMessage: "no, cancela",
  placeholder: "Ej: sube 20% los fines de semana de agosto",
};

type Shape = typeof es;

const en: Shape = {
  title: "Agent chat",
  greeting: "Hi 👋 Ask me about prices or request changes; I propose and you confirm.",
  unreachable: "Couldn't reach the agent. Is the API running on :8000?",
  running: (tool: string) => `Running: ${tool}…`,
  thinking: "Thinking…",
  confirmMessage: "yes, confirm",
  cancelMessage: "no, cancel",
  placeholder: "E.g. raise August weekends by 20%",
};

const pt: Shape = {
  title: "Chat do agente",
  greeting: "Olá 👋 Pergunte sobre preços ou peça alterações; eu proponho e você confirma.",
  unreachable: "Não consegui falar com o agente. A API está rodando em :8000?",
  running: (tool: string) => `Executando: ${tool}…`,
  thinking: "Pensando…",
  confirmMessage: "sim, confirmo",
  cancelMessage: "não, cancele",
  placeholder: "Ex.: suba 20% os fins de semana de agosto",
};

const catalog = { es, en, pt };
export default catalog;
