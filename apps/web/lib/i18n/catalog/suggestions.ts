// Textos del área "suggestions" (feature 021). El español es la referencia: en/pt deben
// tener EXACTAMENTE las mismas claves (TypeScript falla si falta o sobra alguna).
const es = {
  // Página
  title: "Sugerencias",
  intro:
    "Solo noches que todavía puedes vender, agrupadas por evento o periodo. Marca las que quieras y aplícalas juntas con una sola revisión.",
  loadError: "No se pudieron cargar las sugerencias.",
  empty: "No hay sugerencias para noches libres.",
  hiddenOccupiedLong: (n: number) =>
    n === 1
      ? "1 noche con sugerencia está oculta por estar reservada o bloqueada."
      : `${n} noches con sugerencia están ocultas por estar reservadas o bloqueadas.`,
  hiddenOccupiedShort: (n: number) => `${n} noche${n !== 1 ? "s" : ""} oculta${n !== 1 ? "s" : ""} (reservadas o bloqueadas)`,
  blocksCount: (n: number) => `${n} bloque${n !== 1 ? "s" : ""}`,
  clearSelection: "Quitar selección",
  selectedCount: (n: number) => `${n} sugerencia${n !== 1 ? "s" : ""}`,
  preview: "Previsualizar",
  fallbackTitle: (id: number) => `Sugerencia ${id}`,
  rejected: "Sugerencia rechazada",
  publishFailed: (n: number) =>
    `${n} noche${n !== 1 ? "s" : ""} no se ${n !== 1 ? "pudieron" : "pudo"} publicar; esas sugerencias siguen pendientes`,
  applied: (n: number) => `${n} noche${n !== 1 ? "s" : ""} aplicada${n !== 1 ? "s" : ""} y publicada${n !== 1 ? "s" : ""}`,

  // Bloque
  periodGap: "Libre próximo",
  periodOccupancy: "Ocupación alta",
  periodOther: "Otras",
  dirUp: "sube",
  dirDown: "baja",
  dirMixed: "sube y baja",
  selectBlock: (title: string) => `Seleccionar ${title}`,
  selectSuggestion: (range: string) => `Seleccionar sugerencia ${range}`,
  occupiedNote: (sellable: number, total: number, occupied: number) =>
    `${sellable} de ${total} noches · ${occupied} ya reservada${occupied !== 1 ? "s" : ""} o bloqueada${occupied !== 1 ? "s" : ""}`,
  applyOnlyThis: "Aplicar solo esta",
  reject: "Rechazar",

  // Vista previa del lote
  resultTitle: "Resultado",
  previewTitle: "Vista previa de los cambios",
  /** [texto antes del número, texto después del número] */
  willPublish: (n: number): [string, string] => [
    n !== 1 ? "Se publicarán" : "Se publicará",
    `noche${n !== 1 ? "s" : ""} en Booking.com y Airbnb`,
  ],
  skippedNote: (n: number) => `${n} se omite${n !== 1 ? "n" : ""} (ver motivo)`,
  colNight: "Noche",
  colSource: "Origen",
  colChange: "Antes → después",
  skippedReason: (reason: string) => `omitida: ${reason}`,
  previewAgain: "Volver a previsualizar",
  publishing: "Publicando…",
  confirmPublish: "Confirmar y publicar",
  statusApplied: "aplicada",
  statusSkipped: "omitida",
  statusFailed: "falló",
  resultApplied: (n: number) => `${n} aplicada${n !== 1 ? "s" : ""}`,
  resultSkipped: (n: number) => `${n} omitida${n !== 1 ? "s" : ""}`,
  resultFailed: (n: number) => `${n} ${n !== 1 ? "fallaron (siguen pendientes)" : "falló (sigue pendiente)"}`,
};

type Shape = typeof es;

const en: Shape = {
  title: "Suggestions",
  intro:
    "Only nights you can still sell, grouped by event or period. Select the ones you want and apply them together after a single review.",
  loadError: "Couldn't load suggestions.",
  empty: "No suggestions for open nights.",
  hiddenOccupiedLong: (n: number) =>
    n === 1
      ? "1 night with a suggestion is hidden because it's booked or blocked."
      : `${n} nights with suggestions are hidden because they're booked or blocked.`,
  hiddenOccupiedShort: (n: number) => `${n} night${n !== 1 ? "s" : ""} hidden (booked or blocked)`,
  blocksCount: (n: number) => `${n} block${n !== 1 ? "s" : ""}`,
  clearSelection: "Clear selection",
  selectedCount: (n: number) => `${n} suggestion${n !== 1 ? "s" : ""}`,
  preview: "Preview",
  fallbackTitle: (id: number) => `Suggestion ${id}`,
  rejected: "Suggestion rejected",
  publishFailed: (n: number) =>
    `${n} night${n !== 1 ? "s" : ""} couldn't be published; those suggestions are still pending`,
  applied: (n: number) => `${n} night${n !== 1 ? "s" : ""} applied and published`,

  periodGap: "Open soon",
  periodOccupancy: "High occupancy",
  periodOther: "Other",
  dirUp: "up",
  dirDown: "down",
  dirMixed: "up & down",
  selectBlock: (title: string) => `Select ${title}`,
  selectSuggestion: (range: string) => `Select suggestion ${range}`,
  occupiedNote: (sellable: number, total: number, occupied: number) =>
    `${sellable} of ${total} nights · ${occupied} already booked or blocked`,
  applyOnlyThis: "Apply only this",
  reject: "Reject",

  resultTitle: "Result",
  previewTitle: "Preview changes",
  willPublish: (n: number): [string, string] => [
    "",
    `night${n !== 1 ? "s" : ""} will be published to Booking.com and Airbnb`,
  ],
  skippedNote: (n: number) => `${n} skipped (see reason)`,
  colNight: "Night",
  colSource: "Source",
  colChange: "Before → after",
  skippedReason: (reason: string) => `skipped: ${reason}`,
  previewAgain: "Preview again",
  publishing: "Publishing…",
  confirmPublish: "Confirm and publish",
  statusApplied: "applied",
  statusSkipped: "skipped",
  statusFailed: "failed",
  resultApplied: (n: number) => `${n} applied`,
  resultSkipped: (n: number) => `${n} skipped`,
  resultFailed: (n: number) => `${n} failed (still pending)`,
};

const pt: Shape = {
  title: "Sugestões",
  intro:
    "Só noites que você ainda pode vender, agrupadas por evento ou período. Marque as que quiser e aplique todas juntas com uma única revisão.",
  loadError: "Não foi possível carregar as sugestões.",
  empty: "Não há sugestões para noites livres.",
  hiddenOccupiedLong: (n: number) =>
    n === 1
      ? "1 noite com sugestão está oculta por estar reservada ou bloqueada."
      : `${n} noites com sugestão estão ocultas por estarem reservadas ou bloqueadas.`,
  hiddenOccupiedShort: (n: number) => `${n} noite${n !== 1 ? "s" : ""} oculta${n !== 1 ? "s" : ""} (reservadas ou bloqueadas)`,
  blocksCount: (n: number) => `${n} bloco${n !== 1 ? "s" : ""}`,
  clearSelection: "Limpar seleção",
  selectedCount: (n: number) => `${n} ${n !== 1 ? "sugestões" : "sugestão"}`,
  preview: "Pré-visualizar",
  fallbackTitle: (id: number) => `Sugestão ${id}`,
  rejected: "Sugestão rejeitada",
  publishFailed: (n: number) =>
    `${n} noite${n !== 1 ? "s" : ""} não ${n !== 1 ? "puderam" : "pôde"} ser publicada${n !== 1 ? "s" : ""}; essas sugestões continuam pendentes`,
  applied: (n: number) => `${n} noite${n !== 1 ? "s" : ""} aplicada${n !== 1 ? "s" : ""} e publicada${n !== 1 ? "s" : ""}`,

  periodGap: "Livre em breve",
  periodOccupancy: "Ocupação alta",
  periodOther: "Outras",
  dirUp: "sobe",
  dirDown: "desce",
  dirMixed: "sobe e desce",
  selectBlock: (title: string) => `Selecionar ${title}`,
  selectSuggestion: (range: string) => `Selecionar sugestão ${range}`,
  occupiedNote: (sellable: number, total: number, occupied: number) =>
    `${sellable} de ${total} noites · ${occupied} já reservada${occupied !== 1 ? "s" : ""} ou bloqueada${occupied !== 1 ? "s" : ""}`,
  applyOnlyThis: "Aplicar só esta",
  reject: "Rejeitar",

  resultTitle: "Resultado",
  previewTitle: "Pré-visualização das alterações",
  willPublish: (n: number): [string, string] => [
    n !== 1 ? "Serão publicadas" : "Será publicada",
    `noite${n !== 1 ? "s" : ""} no Booking.com e no Airbnb`,
  ],
  skippedNote: (n: number) => `${n} ${n !== 1 ? "serão omitidas" : "será omitida"} (ver motivo)`,
  colNight: "Noite",
  colSource: "Origem",
  colChange: "Antes → depois",
  skippedReason: (reason: string) => `omitida: ${reason}`,
  previewAgain: "Pré-visualizar novamente",
  publishing: "Publicando…",
  confirmPublish: "Confirmar e publicar",
  statusApplied: "aplicada",
  statusSkipped: "omitida",
  statusFailed: "falhou",
  resultApplied: (n: number) => `${n} aplicada${n !== 1 ? "s" : ""}`,
  resultSkipped: (n: number) => `${n} omitida${n !== 1 ? "s" : ""}`,
  resultFailed: (n: number) => `${n} ${n !== 1 ? "falharam (continuam pendentes)" : "falhou (continua pendente)"}`,
};

const catalog = { es, en, pt };
export default catalog;
