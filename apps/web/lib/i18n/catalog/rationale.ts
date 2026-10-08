// Explicación de las sugerencias (feature 021): se compone desde los factores
// estructurados del motor. Nombres de eventos, lugares y fuentes NO se traducen.
const es = {
  relevance: { high: "alta", medium: "media", low: "baja" } as Record<string, string>,
  event: (name: string, rel: string, pct: string) => `${name} (relevancia ${rel}, ${pct})`,
  occupancy: (pct: string) => `ocupación alta alrededor (${pct})`,
  gap: (days: number, pct: string) => `libre a ${days} día${days !== 1 ? "s" : ""} (${pct})`,
  marketUsed: (adr: string, samples: number, weight: number) =>
    `mercado de la zona ~${adr} (${samples} tarifas; pesa ${weight}%)`,
  marketLow: (adr: string, samples: number) =>
    `mercado ~${adr} pero con solo ${samples} tarifa(s): confianza baja, no se usa como ancla`,
  marketDiscarded: (adr: string) =>
    `mercado ~${adr} descartado: no es comparable con tu tarifa`,
  source: "fuente",
};

type Shape = typeof es;

const en: Shape = {
  relevance: { high: "high", medium: "medium", low: "low" },
  event: (name, rel, pct) => `${name} (${rel} relevance, ${pct})`,
  occupancy: (pct) => `high occupancy around these dates (${pct})`,
  gap: (days, pct) => `still free ${days} day${days !== 1 ? "s" : ""} out (${pct})`,
  marketUsed: (adr, samples, weight) => `local market ~${adr} (${samples} rates; weighs ${weight}%)`,
  marketLow: (adr, samples) =>
    `market ~${adr} but only ${samples} rate(s): low confidence, not used as an anchor`,
  marketDiscarded: (adr) => `market ~${adr} discarded: not comparable with your rate`,
  source: "source",
};

const pt: Shape = {
  relevance: { high: "alta", medium: "média", low: "baixa" },
  event: (name, rel, pct) => `${name} (relevância ${rel}, ${pct})`,
  occupancy: (pct) => `ocupação alta nas datas próximas (${pct})`,
  gap: (days, pct) => `livre a ${days} dia${days !== 1 ? "s" : ""} (${pct})`,
  marketUsed: (adr, samples, weight) => `mercado da região ~${adr} (${samples} tarifas; peso ${weight}%)`,
  marketLow: (adr, samples) =>
    `mercado ~${adr}, mas com apenas ${samples} tarifa(s): confiança baixa, não é usado como âncora`,
  marketDiscarded: (adr) => `mercado ~${adr} descartado: não é comparável com a sua tarifa`,
  source: "fonte",
};

const catalog = { es, en, pt };
export default catalog;
