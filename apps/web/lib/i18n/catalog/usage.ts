// Feature 027: uso y límites de IA. El español es la referencia: en/pt con las MISMAS claves.
const es = {
  card: {
    title: "Uso del asistente",
    description: "Mensajes al asistente de este mes. Las sugerencias diarias no cuentan.",
    messages: (used: number, limit: number) => `${used} de ${limit} mensajes`,
    resets: (date: string) => `Se renueva el ${date}.`,
    searches: (n: number, limit: number) => `Búsquedas del escaneo de hoy: ${n} de ${limit}.`,
  },
  warning: (used: number, limit: number) =>
    `Llevas ${used} de ${limit} mensajes al asistente este mes.`,
  exhausted: (date: string) =>
    `Llegaste al límite de mensajes de este mes; se renueva el ${date}.`,
  admin: {
    title: "Uso de IA",
    description:
      "Mensajes al asistente, llamadas a la IA, búsquedas web y costo estimado por cuenta. " +
      "Sin contenido de conversaciones.",
    month: "Mes",
    total: (usd: string) => `Total del mes: USD ${usd}`,
    messages: "Mensajes",
    calls: "Llamadas IA",
    tokens: "Tokens",
    searches: "Búsquedas",
    cost: "Costo (USD)",
    limits: "Límites (mensajes/mes · búsquedas/día)",
    save: "Guardar",
    saved: "Límites guardados",
    reset: "Por defecto",
    unpriced: (n: number) => `${n} llamadas sin precio configurado`,
    empty: "Sin uso este mes.",
  },
};

type Shape = typeof es;

const en: Shape = {
  card: {
    title: "Assistant usage",
    description: "Messages to the assistant this month. Daily suggestions don't count.",
    messages: (used, limit) => `${used} of ${limit} messages`,
    resets: (date) => `Renews on ${date}.`,
    searches: (n, limit) => `Scan searches today: ${n} of ${limit}.`,
  },
  warning: (used, limit) => `You've used ${used} of ${limit} assistant messages this month.`,
  exhausted: (date) => `You reached this month's message limit; it renews on ${date}.`,
  admin: {
    title: "AI usage",
    description:
      "Assistant messages, AI calls, web searches and estimated cost per account. " +
      "No conversation content.",
    month: "Month",
    total: (usd) => `Month total: USD ${usd}`,
    messages: "Messages",
    calls: "AI calls",
    tokens: "Tokens",
    searches: "Searches",
    cost: "Cost (USD)",
    limits: "Limits (messages/month · searches/day)",
    save: "Save",
    saved: "Limits saved",
    reset: "Default",
    unpriced: (n) => `${n} calls without a configured price`,
    empty: "No usage this month.",
  },
};

const pt: Shape = {
  card: {
    title: "Uso do assistente",
    description: "Mensagens ao assistente neste mês. As sugestões diárias não contam.",
    messages: (used, limit) => `${used} de ${limit} mensagens`,
    resets: (date) => `Renova em ${date}.`,
    searches: (n, limit) => `Buscas da varredura hoje: ${n} de ${limit}.`,
  },
  warning: (used, limit) => `Você usou ${used} de ${limit} mensagens ao assistente neste mês.`,
  exhausted: (date) => `Você atingiu o limite de mensagens deste mês; renova em ${date}.`,
  admin: {
    title: "Uso de IA",
    description:
      "Mensagens ao assistente, chamadas à IA, buscas na web e custo estimado por conta. " +
      "Sem conteúdo das conversas.",
    month: "Mês",
    total: (usd) => `Total do mês: USD ${usd}`,
    messages: "Mensagens",
    calls: "Chamadas IA",
    tokens: "Tokens",
    searches: "Buscas",
    cost: "Custo (USD)",
    limits: "Limites (mensagens/mês · buscas/dia)",
    save: "Salvar",
    saved: "Limites salvos",
    reset: "Padrão",
    unpriced: (n) => `${n} chamadas sem preço configurado`,
    empty: "Sem uso neste mês.",
  },
};

const catalog = { es, en, pt };
export default catalog;
