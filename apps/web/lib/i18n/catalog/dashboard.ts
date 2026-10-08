// Textos del área "dashboard" (feature 021). El español es la referencia: en/pt deben
// tener EXACTAMENTE las mismas claves (TypeScript falla si falta o sobra alguna).
const es = {
  title: "Panorama",
  occupancy: "Ocupación (mes)",
  occupiedNights: (n: number) => `${n} noche${n !== 1 ? "s" : ""} ocupada${n !== 1 ? "s" : ""}`,
  reservedNights: "Noches reservadas (mes)",
  blockedNights: "Noches bloqueadas (mes)",
  blockedHint: "bloqueo global: cierra todos los canales",
  pendingSuggestions: "Sugerencias pendientes",
  promoDays: "Días con promoción",
  channels: "Canales",
  direct: "Directo",
  noChannelData: "Sin datos de canales (sincroniza para actualizar).",
  connected: "Conectado",
  inactive: "Inactivo",
  bookings: (n: number) => `${n} ${n === 1 ? "reserva" : "reservas"}`,
  recentSuggestions: "Sugerencias recientes",
  noPendingSuggestions: "Sin sugerencias pendientes.",
};

type Shape = typeof es;

const en: Shape = {
  title: "Overview",
  occupancy: "Occupancy (month)",
  occupiedNights: (n: number) => `${n} night${n !== 1 ? "s" : ""} occupied`,
  reservedNights: "Booked nights (month)",
  blockedNights: "Blocked nights (month)",
  blockedHint: "global block: closes all channels",
  pendingSuggestions: "Pending suggestions",
  promoDays: "Days with a promotion",
  channels: "Channels",
  direct: "Direct",
  noChannelData: "No channel data yet (sync to update).",
  connected: "Connected",
  inactive: "Inactive",
  bookings: (n: number) => `${n} ${n === 1 ? "booking" : "bookings"}`,
  recentSuggestions: "Recent suggestions",
  noPendingSuggestions: "No pending suggestions.",
};

const pt: Shape = {
  title: "Visão geral",
  occupancy: "Ocupação (mês)",
  occupiedNights: (n: number) => `${n} noite${n !== 1 ? "s" : ""} ocupada${n !== 1 ? "s" : ""}`,
  reservedNights: "Noites reservadas (mês)",
  blockedNights: "Noites bloqueadas (mês)",
  blockedHint: "bloqueio global: fecha todos os canais",
  pendingSuggestions: "Sugestões pendentes",
  promoDays: "Dias com promoção",
  channels: "Canais",
  direct: "Direto",
  noChannelData: "Sem dados de canais (sincronize para atualizar).",
  connected: "Conectado",
  inactive: "Inativo",
  bookings: (n: number) => `${n} ${n === 1 ? "reserva" : "reservas"}`,
  recentSuggestions: "Sugestões recentes",
  noPendingSuggestions: "Nenhuma sugestão pendente.",
};

const catalog = { es, en, pt };
export default catalog;
