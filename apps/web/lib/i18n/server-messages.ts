import { getActiveLang, type Lang } from "@/lib/i18n/core";

/** Traducción de los mensajes que produce el servidor (feature 021).
 *
 *  La API sigue hablando español (idioma de referencia). Aquí se traducen al idioma
 *  activo: primero por coincidencia exacta y luego por patrones con parámetros. Sin
 *  coincidencia → se muestra el español original (nunca vacío ni un código interno).
 *  Para agregar uno: copia el texto EXACTO que envía la API y añade en/pt.
 */

type Tr = { en: string; pt: string };

const EXACT: Record<string, Tr> = {
  // --- motivos de omisión y estados (vistas previas / lote) ---
  reservada: { en: "booked", pt: "reservada" },
  bloqueada: { en: "blocked", pt: "bloqueada" },
  pasada: { en: "past date", pt: "data passada" },
  "fuera de límites": { en: "outside price limits", pt: "fora dos limites" },
  "sugerencia resuelta": { en: "suggestion already resolved", pt: "sugestão já resolvida" },
  conflicto: { en: "conflict", pt: "conflito" },
  "por debajo del precio mínimo": { en: "below the minimum price", pt: "abaixo do preço mínimo" },
  "menos de 1 %": { en: "less than 1%", pt: "menos de 1%" },
  "Las bajadas se aplican como promoción desde la vista previa del lote": {
    en: "Price decreases are applied as a promotion from the batch preview",
    pt: "As reduções são aplicadas como promoção a partir da pré-visualização do lote",
  },
  "El precio mínimo debe ser mayor que 0": {
    en: "The minimum price must be greater than 0",
    pt: "O preço mínimo deve ser maior que 0",
  },
  "La acumulación debe ser always o conditional": {
    en: "Stacking must be always or conditional",
    pt: "O acúmulo deve ser always ou conditional",
  },
  "no se pudo publicar al canal": { en: "couldn't publish to the channel", pt: "não foi possível publicar no canal" },
  "clave inválida": { en: "invalid key", pt: "chave inválida" },
  "conflicto al guardar la reserva; el cron lo corregirá": {
    en: "conflict while saving the booking; the daily sync will fix it",
    pt: "conflito ao salvar a reserva; a sincronização diária vai corrigir",
  },
  // --- sugerencias ---
  "La vista previa cambió (precios, reservas o sugerencias); revísala de nuevo.": {
    en: "The preview changed (prices, bookings or suggestions); please review it again.",
    pt: "A pré-visualização mudou (preços, reservas ou sugestões); revise-a novamente.",
  },
  "Selecciona al menos una sugerencia": { en: "Select at least one suggestion", pt: "Selecione pelo menos uma sugestão" },
  "La sugerencia no tiene unidad asignada": {
    en: "The suggestion has no unit assigned",
    pt: "A sugestão não tem unidade atribuída",
  },
  "El precio sugerido viola la regla de precios vigente; no se aplicó nada": {
    en: "The suggested price breaks the current pricing rule; nothing was applied",
    pt: "O preço sugerido viola a regra de preços vigente; nada foi aplicado",
  },
  "no se pudo publicar el precio al canal; la sugerencia sigue pendiente": {
    en: "couldn't publish the price to the channel; the suggestion is still pending",
    pt: "não foi possível publicar o preço no canal; a sugestão continua pendente",
  },
  "Solo se aplica una sugerencia 'proposed' o 'approved'": {
    en: "Only a 'proposed' or 'approved' suggestion can be applied",
    pt: "Só é possível aplicar uma sugestão 'proposed' ou 'approved'",
  },
  "Solo se aprueba una sugerencia 'proposed'": {
    en: "Only a 'proposed' suggestion can be approved",
    pt: "Só é possível aprovar uma sugestão 'proposed'",
  },
  // --- promociones / deals ---
  "El descuento debe estar entre 0% y 100%.": { en: "The discount must be between 0% and 100%.", pt: "O desconto deve estar entre 0% e 100%." },
  "El descuento debe estar entre 0 y 100%": { en: "The discount must be between 0 and 100%", pt: "O desconto deve estar entre 0 e 100%" },
  "El precio con descuento debe ser mayor que 0.": { en: "The discounted price must be greater than 0.", pt: "O preço com desconto deve ser maior que 0." },
  "El rango de la promoción está en el pasado.": { en: "The promotion dates are in the past.", pt: "As datas da promoção estão no passado." },
  "Indica un descuento en porcentaje o un precio con descuento.": {
    en: "Enter a percentage discount or a discounted price.",
    pt: "Informe um desconto percentual ou um preço com desconto.",
  },
  "La estancia mínima debe ser al menos 1 noche.": { en: "Minimum stay must be at least 1 night.", pt: "A estadia mínima deve ser de pelo menos 1 noite." },
  "La propuesta quedó obsoleta (cambió el precio base o el estado). Revísala de nuevo.": {
    en: "The proposal is out of date (the base price or status changed). Please review it again.",
    pt: "A proposta ficou desatualizada (mudou o preço base ou o status). Revise-a novamente.",
  },
  "La retirada requiere confirmación.": { en: "Removing it requires confirmation.", pt: "A retirada exige confirmação." },
  "La última noche no puede ser anterior a la primera.": {
    en: "The last night can't be before the first one.",
    pt: "A última noite não pode ser anterior à primeira.",
  },
  "No hay precio base para esas fechas; indica un precio con descuento absoluto.": {
    en: "There's no base price for those dates; enter an absolute discounted price.",
    pt: "Não há preço base para essas datas; informe um preço com desconto absoluto.",
  },
  "el alcance de canales no puede estar vacío (omítelo para 'todos')": {
    en: "the channel scope can't be empty (omit it for 'all')",
    pt: "o escopo de canais não pode ficar vazio (omita para 'todos')",
  },
  "El canal debe ser booking o airbnb": { en: "The channel must be booking or airbnb", pt: "O canal deve ser booking ou airbnb" },
  "El nombre del deal es obligatorio": { en: "The deal name is required", pt: "O nome do deal é obrigatório" },
  "La fecha de fin no puede ser anterior a la de inicio": {
    en: "The end date can't be before the start date",
    pt: "A data final não pode ser anterior à inicial",
  },
  // --- canal / precios ---
  "no hay propiedad sincronizada; importa desde el Channel Manager": {
    en: "no property synced yet; import from the Channel Manager",
    pt: "nenhuma propriedade sincronizada; importe do Channel Manager",
  },
  "la propuesta no corresponde al estado actual; vuelve a previsualizar": {
    en: "the proposal doesn't match the current state; preview it again",
    pt: "a proposta não corresponde ao estado atual; pré-visualize novamente",
  },
  "El cambio objetivo no tiene valor anterior (creación); no se puede revertir.": {
    en: "The target change has no previous value (it was a creation); it can't be reverted.",
    pt: "A alteração não tem valor anterior (foi uma criação); não pode ser revertida.",
  },
  "La API V1 no soporta escritura de disponibilidad; usa la V2.": {
    en: "API V1 can't write availability; use V2.",
    pt: "A API V1 não grava disponibilidade; use a V2.",
  },
  // --- notas, sitios, escaneo ---
  "La nota no puede estar vacía": { en: "The note can't be empty", pt: "A nota não pode ficar vazia" },
  "El nombre del sitio es obligatorio": { en: "The place name is required", pt: "O nome do local é obrigatório" },
  "No existe el sitio": { en: "That place doesn't exist", pt: "Esse local não existe" },
  "Las consultas por corrida deben estar entre 1 y 30": {
    en: "Searches per run must be between 1 and 30",
    pt: "As consultas por execução devem estar entre 1 e 30",
  },
  // --- secretos / Beds24 / avisos ---
  "Secreto no gestionable": { en: "This secret can't be managed here", pt: "Este segredo não pode ser gerenciado aqui" },
  "El valor no puede estar vacío": { en: "The value can't be empty", pt: "O valor não pode ficar vazio" },
  "No hay valor guardado en la app para este secreto": {
    en: "There's no value saved in the app for this secret",
    pt: "Não há valor salvo no app para este segredo",
  },
  "conexión OK": { en: "connection OK", pt: "conexão OK" },
  "credencial rechazada por el proveedor": { en: "credential rejected by the provider", pt: "credencial rejeitada pelo provedor" },
  "servicio no disponible o error de red": { en: "service unavailable or network error", pt: "serviço indisponível ou erro de rede" },
  "sin credencial configurada": { en: "no credential configured", pt: "nenhuma credencial configurada" },
  "sin configurar": { en: "not configured", pt: "não configurado" },
  "clave guardada; sin avisos aún": { en: "key saved; no notifications yet", pt: "chave salva; nenhum aviso ainda" },
  "Beds24 rechazó el token: genera un código de invitación y usa Canjear": {
    en: "Beds24 rejected the token: generate an invite code and use Redeem",
    pt: "O Beds24 rejeitou o token: gere um código de convite e use Resgatar",
  },
  "El código no puede estar vacío": { en: "The code can't be empty", pt: "O código não pode ficar vazio" },
  "Beds24 rechazó el código (¿vencido o ya usado?). Genera uno nuevo.": {
    en: "Beds24 rejected the code (expired or already used?). Generate a new one.",
    pt: "O Beds24 rejeitou o código (expirado ou já usado?). Gere um novo.",
  },
  "Avisos no configurados": { en: "Notifications not configured", pt: "Avisos não configurados" },
  "No autorizado": { en: "Unauthorized", pt: "Não autorizado" },
  "API no disponible": { en: "API unavailable", pt: "API indisponível" },
  "Idioma no soportado": { en: "Unsupported language", pt: "Idioma não suportado" },
  "Aviso demasiado grande": { en: "Notification too large", pt: "Aviso grande demais" },
  // --- avisos al celular (feature 025) ---
  "el teléfono ya no está registrado": {
    en: "the phone is no longer registered",
    pt: "o telefone não está mais registrado",
  },
  "credencial de avisos sin configurar": {
    en: "notification credential not configured",
    pt: "credencial de avisos não configurada",
  },
  "la credencial de avisos no es un JSON válido": {
    en: "the notification credential is not valid JSON",
    pt: "a credencial de avisos não é um JSON válido",
  },
  // --- extender precios (feature 023) ---
  "la fecha final no puede ser anterior a hoy": {
    en: "the end date can't be before today",
    pt: "a data final não pode ser anterior a hoje",
  },
  "la fecha final no puede superar 24 meses desde hoy": {
    en: "the end date can't be more than 24 months from today",
    pt: "a data final não pode passar de 24 meses a partir de hoje",
  },
  "el % de fin de semana debe estar entre 0 y 50": {
    en: "the weekend % must be between 0 and 50",
    pt: "o % de fim de semana deve estar entre 0 e 50",
  },
  // --- cuentas (feature 026) ---
  "Unidad no encontrada": { en: "Unit not found", pt: "Unidade não encontrada" },
  "Conversación no encontrada": { en: "Conversation not found", pt: "Conversa não encontrada" },
  "Esta propiedad ya está conectada a otra cuenta de StayLever": {
    en: "This property is already connected to another StayLever account",
    pt: "Esta propriedade já está conectada a outra conta do StayLever",
  },
  "unidad no encontrada o sin mapear al Channel Manager": {
    en: "unit not found or not mapped to the Channel Manager",
    pt: "unidade não encontrada ou não mapeada no Channel Manager",
  },
  "la vista previa quedó desactualizada; vuelve a previsualizar": {
    en: "the preview is out of date; preview again",
    pt: "a pré-visualização ficou desatualizada; pré-visualize de novo",
  },
  "el calendario no se confirmó al releer": {
    en: "the calendar couldn't be confirmed on re-read",
    pt: "o calendário não foi confirmado ao reler",
  },
};

type Pattern = { re: RegExp; en: (m: RegExpExecArray) => string; pt: (m: RegExpExecArray) => string };

const PATTERNS: Pattern[] = [
  {
    re: /^La sugerencia venció \(rango (.+) → (.+), todo en el pasado\)$/,
    en: (m) => `The suggestion expired (range ${m[1]} → ${m[2]}, all in the past)`,
    pt: (m) => `A sugestão expirou (período ${m[1]} → ${m[2]}, tudo no passado)`,
  },
  {
    re: /^La sugerencia ya está resuelta \(estado real: (.+)\)$/,
    en: (m) => `The suggestion is already resolved (current status: ${m[1]})`,
    pt: (m) => `A sugestão já foi resolvida (status atual: ${m[1]})`,
  },
  {
    re: /^No existe (?:la sugerencia|la promoción|el deal|la nota|el cambio|la unidad) (\d+)\.?$/,
    en: (m) => `Item ${m[1]} doesn't exist`,
    pt: (m) => `O item ${m[1]} não existe`,
  },
  {
    re: /^error al publicar \((\w+)\)$/,
    en: (m) => `publishing error (${m[1]})`,
    pt: (m) => `erro ao publicar (${m[1]})`,
  },
  {
    re: /^Beds24 no respondió \((\w+)\)$/,
    en: (m) => `Beds24 didn't respond (${m[1]})`,
    pt: (m) => `O Beds24 não respondeu (${m[1]})`,
  },
  {
    re: /^conexión OK \((\d+) propiedad(?:es)?\)$/,
    en: (m) => `connection OK (${m[1]} propert${m[1] === "1" ? "y" : "ies"})`,
    pt: (m) => `conexão OK (${m[1]} propriedade${m[1] === "1" ? "" : "s"})`,
  },
  {
    re: /^último aviso: (.+) UTC$/,
    en: (m) => `last notification: ${m[1]} UTC`,
    pt: (m) => `último aviso: ${m[1]} UTC`,
  },
  {
    re: /^La nota supera el máximo de (\d+) caracteres$/,
    en: (m) => `The note exceeds the ${m[1]}-character limit`,
    pt: (m) => `A nota excede o máximo de ${m[1]} caracteres`,
  },
  {
    re: /^canal(?:\(es\))? (?:desconocido|no gestionado(?:\(s\))?): (.+)$/,
    en: (m) => `unknown or unmanaged channel: ${m[1]}`,
    pt: (m) => `canal desconhecido ou não gerenciado: ${m[1]}`,
  },
  {
    re: /^el ajuste debe estar entre (-?\d+)% y (-?\d+)% \(recibido (-?[\d.]+)%\)$/,
    en: (m) => `the adjustment must be between ${m[1]}% and ${m[2]}% (got ${m[3]}%)`,
    pt: (m) => `o ajuste deve estar entre ${m[1]}% e ${m[2]}% (recebido ${m[3]}%)`,
  },
  // --- advertencias del preview de promociones (offer_promotion_service) ---
  {
    re: /^Se solapa con otra promoción activa: (.+)\. Confirma para continuar\.$/,
    en: (m) => `Overlaps another active promotion: ${m[1]}. Confirm to continue.`,
    pt: (m) => `Sobrepõe outra promoção ativa: ${m[1]}. Confirme para continuar.`,
  },
  {
    re: /^Hay (\d+) reserva\(s\) confirmada\(s\) en el rango; sus precios no cambian \(la promoción afecta solo a nuevas reservas\)\.$/,
    en: (m) => `There are ${m[1]} confirmed booking(s) in the range; their prices don't change (the promotion only affects new bookings).`,
    pt: (m) => `Há ${m[1]} reserva(s) confirmada(s) no período; os preços delas não mudam (a promoção só afeta novas reservas).`,
  },
  {
    re: /^Puede duplicar descuento con el deal nativo '(.+)' \((.+), ([\d.]+)%\)\. Revísalo antes de confirmar\.$/,
    en: (m) => `It may stack with the native deal '${m[1]}' (${m[2]}, ${m[3]}%). Review it before confirming.`,
    pt: (m) => `Pode acumular desconto com o deal nativo '${m[1]}' (${m[2]}, ${m[3]}%). Revise antes de confirmar.`,
  },
  {
    re: /^el canal (\S+) está inactivo: el ajuste no tendrá efecto hasta reactivarlo$/,
    en: (m) => `the ${m[1]} channel is inactive: the adjustment won't take effect until it's reactivated`,
    pt: (m) => `o canal ${m[1]} está inativo: o ajuste só terá efeito quando for reativado`,
  },
  // --- avisos al celular (feature 025) ---
  {
    re: /^Firebase OK \(proyecto (.+)\)$/,
    en: (m) => `Firebase OK (project ${m[1]})`,
    pt: (m) => `Firebase OK (projeto ${m[1]})`,
  },
  {
    re: /^Firebase respondió (\d+)$/,
    en: (m) => `Firebase responded ${m[1]}`,
    pt: (m) => `O Firebase respondeu ${m[1]}`,
  },
  {
    re: /^Firebase rechazó la credencial de avisos \((\d+)\)$/,
    en: (m) => `Firebase rejected the notification credential (${m[1]})`,
    pt: (m) => `O Firebase rejeitou a credencial de avisos (${m[1]})`,
  },
  {
    re: /^(?:Firebase no respondió|sin respuesta de Firebase) \((\w+)\)$/,
    en: (m) => `Firebase didn't respond (${m[1]})`,
    pt: (m) => `O Firebase não respondeu (${m[1]})`,
  },
  {
    re: /^a la credencial de avisos le falta (\w+)$/,
    en: (m) => `the notification credential is missing ${m[1]}`,
    pt: (m) => `falta ${m[1]} na credencial de avisos`,
  },
  {
    re: /^No existe el teléfono (\d+)$/,
    en: (m) => `Phone ${m[1]} doesn't exist`,
    pt: (m) => `O telefone ${m[1]} não existe`,
  },
  // --- extender precios (feature 023) ---
  {
    re: /^precio confirmado; la apertura no se confirmó en (\d+) noche\(s\)$/,
    en: (m) => `price confirmed; opening not confirmed on ${m[1]} night(s)`,
    pt: (m) => `preço confirmado; a abertura não foi confirmada em ${m[1]} noite(s)`,
  },
  {
    re: /^el calendario no se confirmó al releer \(respuesta: (.*)\)$/s,
    en: (m) => `the calendar couldn't be confirmed on re-read (response: ${m[1]})`,
    pt: (m) => `o calendário não foi confirmado ao reler (resposta: ${m[1]})`,
  },
  {
    re: /^el precio de (\d{4}-\d{2}) debe ser mayor que 0$/,
    en: (m) => `the price for ${m[1]} must be greater than 0`,
    pt: (m) => `o preço de ${m[1]} deve ser maior que 0`,
  },
  {
    re: /^falta el precio de (\d{4}-\d{2})$/,
    en: (m) => `the price for ${m[1]} is missing`,
    pt: (m) => `falta o preço de ${m[1]}`,
  },
  {
    re: /^no se pudo leer el Channel Manager: (.+)$/,
    en: (m) => `couldn't read the Channel Manager: ${m[1]}`,
    pt: (m) => `não foi possível ler o Channel Manager: ${m[1]}`,
  },
  {
    re: /^error al publicar \((.+)\)$/,
    en: (m) => `publishing error (${m[1]})`,
    pt: (m) => `erro ao publicar (${m[1]})`,
  },
  {
    re: /^API (\d+) en (.+)$/,
    en: (m) => `API ${m[1]} at ${m[2]}`,
    pt: (m) => `API ${m[1]} em ${m[2]}`,
  },
];

/** Traduce un mensaje del servidor al idioma indicado (por defecto, el activo). */
export function trServer(message: string | null | undefined, lang: Lang = getActiveLang()): string {
  if (!message) return "";
  if (lang === "es") return message;
  const exact = EXACT[message];
  if (exact) return exact[lang];
  for (const p of PATTERNS) {
    const m = p.re.exec(message);
    if (m) return p[lang](m);
  }
  return message; // sin traducción conocida → español (FR-011)
}
