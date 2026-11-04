// Rentabilidad mensual (feature 042). El español es la referencia.
const es = {
  title: "Rentabilidad",
  intro:
    "Lo que te deja la renta corta cada mes, después de comisiones, aseo y costos fijos, frente a lo que te daría un arriendo tradicional.",
  settingsTitle: "Tus números",
  settingsHint:
    "Se usan solo para este informe. Costos fijos: lo que en un arriendo pagaría el inquilino (servicios, internet, administración, Beds24, reposición).",
  rent: "Arriendo tradicional de referencia (al mes)",
  fixed: "Costos fijos al mes",
  cleaning: "Aseo por estancia",
  save: "Guardar",
  saved: "Guardado",
  last12: "Últimos 12 meses",
  netAvg: "Neto promedio al mes",
  vsRent: "Frente al arriendo",
  occupancy: "Ocupación",
  breakeven: "Noches al mes para igualar el arriendo",
  breakevenHint: (n: number) => `Con tu ingreso neto por noche, hacen falta ${n} noches al mes.`,
  noRent: "Escribe el arriendo de referencia para comparar.",
  month: "Mes",
  nights: "Noches",
  gross: "Ingreso",
  commission: "Comisiones",
  costs: "Aseo + fijos",
  net: "Neto",
  diff: "vs. arriendo",
  estimated: "estimado",
  estimatedHint:
    "Estimado: algunas reservas no traen el valor del canal (o falta la TRM) y se calcularon con el precio del calendario y una comisión típica.",
  future: "en curso / reservado",
  better: "mejor que el arriendo",
  worse: "peor que el arriendo",
  empty: "Aún no hay reservas en este periodo.",
  usdNote: "Las reservas de Airbnb en dólares se pasan a pesos con la TRM del día de llegada.",
};

type Shape = typeof es;

const en: Shape = {
  title: "Profitability",
  intro:
    "What short-term renting leaves you each month after commissions, cleaning and fixed costs, compared with a traditional long-term lease.",
  settingsTitle: "Your numbers",
  settingsHint:
    "Used only for this report. Fixed costs: what a long-term tenant would pay (utilities, internet, building fees, Beds24, replacements).",
  rent: "Reference long-term rent (per month)",
  fixed: "Fixed costs per month",
  cleaning: "Cleaning per stay",
  save: "Save",
  saved: "Saved",
  last12: "Last 12 months",
  netAvg: "Average net per month",
  vsRent: "Versus long-term rent",
  occupancy: "Occupancy",
  breakeven: "Nights per month to match the rent",
  breakevenHint: (n: number) => `With your net income per night, you need ${n} nights a month.`,
  noRent: "Enter the reference rent to compare.",
  month: "Month",
  nights: "Nights",
  gross: "Income",
  commission: "Commissions",
  costs: "Cleaning + fixed",
  net: "Net",
  diff: "vs. rent",
  estimated: "estimated",
  estimatedHint:
    "Estimated: some bookings don't include the channel amount (or the exchange rate is missing) and were computed from the calendar price and a typical commission.",
  future: "in progress / booked",
  better: "better than renting",
  worse: "worse than renting",
  empty: "No bookings in this period yet.",
  usdNote: "Airbnb bookings in US dollars are converted with the official rate (TRM) of the arrival date.",
};

const pt: Shape = {
  title: "Rentabilidade",
  intro:
    "Quanto a locação por temporada te deixa por mês, depois de comissões, limpeza e custos fixos, comparado com um aluguel tradicional.",
  settingsTitle: "Seus números",
  settingsHint:
    "Usados só neste relatório. Custos fixos: o que um inquilino de longo prazo pagaria (contas, internet, condomínio, Beds24, reposição).",
  rent: "Aluguel tradicional de referência (por mês)",
  fixed: "Custos fixos por mês",
  cleaning: "Limpeza por estadia",
  save: "Salvar",
  saved: "Salvo",
  last12: "Últimos 12 meses",
  netAvg: "Líquido médio por mês",
  vsRent: "Comparado ao aluguel",
  occupancy: "Ocupação",
  breakeven: "Noites por mês para igualar o aluguel",
  breakevenHint: (n: number) => `Com sua receita líquida por noite, são necessárias ${n} noites por mês.`,
  noRent: "Informe o aluguel de referência para comparar.",
  month: "Mês",
  nights: "Noites",
  gross: "Receita",
  commission: "Comissões",
  costs: "Limpeza + fixos",
  net: "Líquido",
  diff: "vs. aluguel",
  estimated: "estimado",
  estimatedHint:
    "Estimado: algumas reservas não trazem o valor do canal (ou falta a cotação) e foram calculadas com o preço do calendário e uma comissão típica.",
  future: "em andamento / reservado",
  better: "melhor que o aluguel",
  worse: "pior que o aluguel",
  empty: "Ainda não há reservas neste período.",
  usdNote: "As reservas do Airbnb em dólares são convertidas com a cotação oficial (TRM) do dia de chegada.",
};

const catalog = { es, en, pt };
export default catalog;
