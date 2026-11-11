// Mensajes de huéspedes (feature 045). El español es la referencia.
const es = {
  title: "Mensajes",
  intro: "Conversaciones con tus huéspedes de Airbnb y Booking.com, a través de Beds24.",
  empty: "No hay mensajes de los últimos 90 días.",
  unavailable: "Los mensajes requieren conectar Beds24.",
  connect: "Conectar Beds24",
  unread: (n: number) => `${n} sin leer`,
  you: "Tú",
  guest: "Huésped",
  system: "Plataforma",
  note: "Nota interna",
  pick: "Elige una conversación.",
  placeholder: "Escribe tu respuesta…",
  send: "Enviar",
  sending: "Enviando…",
  sent: "Mensaje enviado",
  suggest: "Sugerir respuesta",
  suggesting: "Pensando…",
  suggestHint:
    "La IA propone un borrador sin ver nombres, correos ni teléfonos. Revísalo y complétalo antes de enviar: nada se envía solo.",
  cantReply: "Esta reserva no es de Airbnb ni Booking.com: respóndela por su canal.",
  back: "Volver",
  stay: (from: string, to: string) => `${from} → ${to}`,
};

type Shape = typeof es;

const en: Shape = {
  title: "Messages",
  intro: "Conversations with your Airbnb and Booking.com guests, through Beds24.",
  empty: "No messages in the last 90 days.",
  unavailable: "Messages require connecting Beds24.",
  connect: "Connect Beds24",
  unread: (n: number) => `${n} unread`,
  you: "You",
  guest: "Guest",
  system: "Platform",
  note: "Internal note",
  pick: "Choose a conversation.",
  placeholder: "Write your reply…",
  send: "Send",
  sending: "Sending…",
  sent: "Message sent",
  suggest: "Suggest a reply",
  suggesting: "Thinking…",
  suggestHint:
    "The AI drafts a reply without seeing names, emails or phone numbers. Review and complete it before sending: nothing is sent automatically.",
  cantReply: "This booking isn't from Airbnb or Booking.com: reply through its channel.",
  back: "Back",
  stay: (from: string, to: string) => `${from} → ${to}`,
};

const pt: Shape = {
  title: "Mensagens",
  intro: "Conversas com seus hóspedes do Airbnb e do Booking.com, pelo Beds24.",
  empty: "Não há mensagens dos últimos 90 dias.",
  unavailable: "As mensagens exigem conectar o Beds24.",
  connect: "Conectar o Beds24",
  unread: (n: number) => `${n} não lida${n === 1 ? "" : "s"}`,
  you: "Você",
  guest: "Hóspede",
  system: "Plataforma",
  note: "Nota interna",
  pick: "Escolha uma conversa.",
  placeholder: "Escreva sua resposta…",
  send: "Enviar",
  sending: "Enviando…",
  sent: "Mensagem enviada",
  suggest: "Sugerir resposta",
  suggesting: "Pensando…",
  suggestHint:
    "A IA sugere um rascunho sem ver nomes, e-mails nem telefones. Revise e complete antes de enviar: nada é enviado sozinho.",
  cantReply: "Esta reserva não é do Airbnb nem do Booking.com: responda pelo canal dela.",
  back: "Voltar",
  stay: (from: string, to: string) => `${from} → ${to}`,
};

const catalog = { es, en, pt };
export default catalog;
