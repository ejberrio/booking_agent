// Textos de "Extender precios" y del aviso de horizonte (feature 023). El español es la
// referencia: en/pt deben tener EXACTAMENTE las mismas claves.
const es = {
  // --- aviso ---
  bannerTitle: "Pocos meses con precio",
  bannerText: (until: string, months: number) =>
    `Tienes precio solo hasta el ${until} (${months} ${months === 1 ? "mes" : "meses"}). ` +
    "Después de esa fecha el apartamento no se puede reservar.",
  extendCta: "Extender precios",
  // --- diálogo ---
  title: "Extender precios hacia el futuro",
  intro:
    "Carga precio en las noches futuras que no tienen, con una plantilla por mes. " +
    "Las noches que ya tienen precio no se tocan.",
  until: "Hasta",
  weekendPct: "Extra viernes y sábado (%)",
  openClosed: "Abrir las noches cerradas sin precio",
  openClosedHint: "Las que bloqueaste desde la app siguen cerradas.",
  colMonth: "Mes",
  colPrice: "Precio por noche",
  colNights: "Noches",
  colDetail: "Detalle",
  include: "Incluir",
  proposed: (p: string) => `propuesto ${p}`,
  weekendShort: (p: string) => `vie–sáb ${p}`,
  toOpen: (n: number) => `${n} se abren`,
  keptClosed: (n: number) => `${n} siguen cerradas`,
  clippedMin: (n: number) => `${n} ajustadas al mínimo`,
  clippedMax: (n: number) => `${n} ajustadas al máximo`,
  refresh: "Recalcular vista previa",
  nothing: "No hay noches sin precio hasta esa fecha.",
  minNote: (p: string) => `Ningún precio queda por debajo de tu mínimo (${p}).`,
  noMin: "Sin precio mínimo configurado.",
  totals: (nights: number, open: number) =>
    `${nights} noche${nights !== 1 ? "s" : ""} recibirán precio · ${open} se abrirán.`,
  confirmCheck: (n: number) =>
    `Entiendo que se publicarán ${n} noche${n !== 1 ? "s" : ""} en Booking.com y Airbnb.`,
  confirm: "Confirmar y publicar",
  cancel: "Cancelar",
  close: "Cerrar",
  editedHint: "Cambiaste la plantilla: recalcula la vista previa antes de confirmar.",
  stale: "Algo cambió en Beds24 desde la vista previa; se recalculó, revísala y confirma de nuevo.",
  resultTitle: "Resultado de la extensión",
  resultSummary: (nights: number, opened: number) =>
    `${nights} noche${nights !== 1 ? "s" : ""} con precio · ${opened} abierta${opened !== 1 ? "s" : ""}.`,
  statusApplied: "publicado",
  statusFailed: "falló",
  statusSkipped: "excluido",
  failedNote: "Los meses fallidos no quedaron con precio; vuelve a extender para reintentarlos.",
  // --- noches con precio pero cerradas ---
  closedPricedNote: (n: number, from: string) =>
    `Ojo: ${n} noche${n !== 1 ? "s" : ""} ya tiene${n !== 1 ? "n" : ""} precio pero está${n !== 1 ? "n" : ""} cerrada${n !== 1 ? "s" : ""} en Beds24 (desde el ${from}), así que no se pueden reservar. Esta extensión no las cambia.`,
  notOpenedTitle: "Algunas noches no se pudieron abrir",
  notOpenedText: (n: number) =>
    `${n} noche${n !== 1 ? "s" : ""} ${n !== 1 ? "quedaron" : "quedó"} con precio pero cerrada${n !== 1 ? "s" : ""}: Beds24 aceptó la orden de abrir${n !== 1 ? "las" : "la"} pero no la aplicó. ` +
    "No se pueden reservar en Booking.com ni en Airbnb hasta que se abran en Beds24.",
  monthNotOpened: (n: number) => `${n} sin abrir`,
  bannerClosedTitle: "Noches con precio que no se pueden reservar",
  bannerClosedText: (n: number, from: string) =>
    `${n} noche${n !== 1 ? "s" : ""} con precio está${n !== 1 ? "n" : ""} cerrada${n !== 1 ? "s" : ""} en el canal desde el ${from}. ` +
    "Ábrelas en Beds24 (o en Calendario → Abrir) para poder recibir reservas.",
};

type Shape = typeof es;

const en: Shape = {
  bannerTitle: "Few months with prices",
  bannerText: (until: string, months: number) =>
    `You only have prices until ${until} (${months} ${months === 1 ? "month" : "months"}). ` +
    "After that date the apartment can't be booked.",
  extendCta: "Extend prices",
  title: "Extend prices into the future",
  intro:
    "Load prices on future nights that don't have one, using a monthly template. " +
    "Nights that already have a price aren't touched.",
  until: "Until",
  weekendPct: "Extra for Friday and Saturday (%)",
  openClosed: "Open closed nights without a price",
  openClosedHint: "Nights you blocked from the app stay closed.",
  colMonth: "Month",
  colPrice: "Price per night",
  colNights: "Nights",
  colDetail: "Details",
  include: "Include",
  proposed: (p: string) => `suggested ${p}`,
  weekendShort: (p: string) => `Fri–Sat ${p}`,
  toOpen: (n: number) => `${n} will open`,
  keptClosed: (n: number) => `${n} stay closed`,
  clippedMin: (n: number) => `${n} raised to the minimum`,
  clippedMax: (n: number) => `${n} lowered to the maximum`,
  refresh: "Recalculate preview",
  nothing: "There are no nights without a price until that date.",
  minNote: (p: string) => `No price goes below your minimum (${p}).`,
  noMin: "No minimum price set.",
  totals: (nights: number, open: number) =>
    `${nights} night${nights !== 1 ? "s" : ""} will get a price · ${open} will open.`,
  confirmCheck: (n: number) =>
    `I understand that ${n} night${n !== 1 ? "s" : ""} will be published on Booking.com and Airbnb.`,
  confirm: "Confirm and publish",
  cancel: "Cancel",
  close: "Close",
  editedHint: "You changed the template: recalculate the preview before confirming.",
  stale: "Something changed in Beds24 since the preview; it was recalculated, review it and confirm again.",
  resultTitle: "Extension result",
  resultSummary: (nights: number, opened: number) =>
    `${nights} night${nights !== 1 ? "s" : ""} priced · ${opened} opened.`,
  statusApplied: "published",
  statusFailed: "failed",
  statusSkipped: "excluded",
  failedNote: "Failed months didn't get prices; extend again to retry them.",
  closedPricedNote: (n: number, from: string) =>
    `Heads-up: ${n} night${n !== 1 ? "s" : ""} already ha${n !== 1 ? "ve" : "s"} a price but ${n !== 1 ? "are" : "is"} closed in Beds24 (from ${from}), so ${n !== 1 ? "they" : "it"} can't be booked. This extension doesn't change ${n !== 1 ? "them" : "it"}.`,
  notOpenedTitle: "Some nights couldn't be opened",
  notOpenedText: (n: number) =>
    `${n} night${n !== 1 ? "s" : ""} got a price but stayed closed: Beds24 accepted the request to open ${n !== 1 ? "them" : "it"} but didn't apply it. ` +
    "They can't be booked on Booking.com or Airbnb until they're opened in Beds24.",
  monthNotOpened: (n: number) => `${n} not opened`,
  bannerClosedTitle: "Priced nights that can't be booked",
  bannerClosedText: (n: number, from: string) =>
    `${n} priced night${n !== 1 ? "s are" : " is"} closed on the channels from ${from}. ` +
    "Open them in Beds24 (or Calendar → Open) to receive bookings.",
};

const pt: Shape = {
  bannerTitle: "Poucos meses com preço",
  bannerText: (until: string, months: number) =>
    `Você só tem preço até ${until} (${months} ${months === 1 ? "mês" : "meses"}). ` +
    "Depois dessa data o apartamento não pode ser reservado.",
  extendCta: "Estender preços",
  title: "Estender preços para o futuro",
  intro:
    "Carrega preço nas noites futuras que não têm, com um modelo por mês. " +
    "As noites que já têm preço não são alteradas.",
  until: "Até",
  weekendPct: "Extra sexta e sábado (%)",
  openClosed: "Abrir as noites fechadas sem preço",
  openClosedHint: "As que você bloqueou pelo app continuam fechadas.",
  colMonth: "Mês",
  colPrice: "Preço por noite",
  colNights: "Noites",
  colDetail: "Detalhe",
  include: "Incluir",
  proposed: (p: string) => `sugerido ${p}`,
  weekendShort: (p: string) => `sex–sáb ${p}`,
  toOpen: (n: number) => `${n} serão abertas`,
  keptClosed: (n: number) => `${n} continuam fechadas`,
  clippedMin: (n: number) => `${n} ajustadas ao mínimo`,
  clippedMax: (n: number) => `${n} ajustadas ao máximo`,
  refresh: "Recalcular pré-visualização",
  nothing: "Não há noites sem preço até essa data.",
  minNote: (p: string) => `Nenhum preço fica abaixo do seu mínimo (${p}).`,
  noMin: "Sem preço mínimo configurado.",
  totals: (nights: number, open: number) =>
    `${nights} noite${nights !== 1 ? "s" : ""} receberão preço · ${open} serão abertas.`,
  confirmCheck: (n: number) =>
    `Entendo que ${n} noite${n !== 1 ? "s" : ""} serão publicadas no Booking.com e no Airbnb.`,
  confirm: "Confirmar e publicar",
  cancel: "Cancelar",
  close: "Fechar",
  editedHint: "Você mudou o modelo: recalcule a pré-visualização antes de confirmar.",
  stale: "Algo mudou no Beds24 desde a pré-visualização; ela foi recalculada, revise e confirme de novo.",
  resultTitle: "Resultado da extensão",
  resultSummary: (nights: number, opened: number) =>
    `${nights} noite${nights !== 1 ? "s" : ""} com preço · ${opened} aberta${opened !== 1 ? "s" : ""}.`,
  statusApplied: "publicado",
  statusFailed: "falhou",
  statusSkipped: "excluído",
  failedNote: "Os meses que falharam ficaram sem preço; estenda de novo para tentar outra vez.",
  closedPricedNote: (n: number, from: string) =>
    `Atenção: ${n} noite${n !== 1 ? "s" : ""} já ${n !== 1 ? "têm" : "tem"} preço mas ${n !== 1 ? "estão fechadas" : "está fechada"} no Beds24 (desde ${from}), então não ${n !== 1 ? "podem" : "pode"} ser reservada${n !== 1 ? "s" : ""}. Esta extensão não as altera.`,
  notOpenedTitle: "Algumas noites não puderam ser abertas",
  notOpenedText: (n: number) =>
    `${n} noite${n !== 1 ? "s" : ""} ${n !== 1 ? "ficaram" : "ficou"} com preço mas fechada${n !== 1 ? "s" : ""}: o Beds24 aceitou a ordem de abrir mas não a aplicou. ` +
    "Não podem ser reservadas no Booking.com nem no Airbnb até serem abertas no Beds24.",
  monthNotOpened: (n: number) => `${n} sem abrir`,
  bannerClosedTitle: "Noites com preço que não podem ser reservadas",
  bannerClosedText: (n: number, from: string) =>
    `${n} noite${n !== 1 ? "s" : ""} com preço ${n !== 1 ? "estão fechadas" : "está fechada"} nos canais desde ${from}. ` +
    "Abra-as no Beds24 (ou em Calendário → Abrir) para receber reservas.",
};

const catalog = { es, en, pt };
export default catalog;
