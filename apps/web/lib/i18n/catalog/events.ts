// Reportar eventos faltantes (feature 035). El español es la referencia: en/pt con las MISMAS claves.
const es = {
  button: "¿Falta un evento?",
  title: "Reportar un evento",
  text:
    "¿Sabes de un concierto, feria o evento cerca de tu apartamento que no aparece? Cuéntanos: " +
    "lo verificamos en la web y, si se confirma, ajustamos tus sugerencias de esas fechas.",
  name: "Nombre del evento (ej.: Hebert Vargas)",
  start: "Fecha",
  end: "Hasta (opcional)",
  venue: "Lugar (opcional, ej.: DAVIarena)",
  submit: "Verificar y agregar",
  checking: "Verificando en la web…",
  limit: "Puedes reportar hasta 3 eventos por día.",
  close: "Cerrar",
  exists: "Ya lo teníamos",
  verified: "Confirmado",
  unverified: "Sin confirmar",
};

type Shape = typeof es;

const en: Shape = {
  button: "Missing an event?",
  title: "Report an event",
  text:
    "Know of a concert, fair or event near your apartment that isn't listed? Tell us: we check " +
    "it on the web and, if confirmed, adjust your suggestions for those dates.",
  name: "Event name (e.g. Hebert Vargas)",
  start: "Date",
  end: "Until (optional)",
  venue: "Venue (optional, e.g. DAVIarena)",
  submit: "Check and add",
  checking: "Checking on the web…",
  limit: "You can report up to 3 events per day.",
  close: "Close",
  exists: "Already listed",
  verified: "Confirmed",
  unverified: "Not confirmed",
};

const pt: Shape = {
  button: "Falta um evento?",
  title: "Informar um evento",
  text:
    "Sabe de um show, feira ou evento perto do seu apartamento que não aparece? Conte para nós: " +
    "verificamos na web e, se confirmado, ajustamos suas sugestões dessas datas.",
  name: "Nome do evento (ex.: Hebert Vargas)",
  start: "Data",
  end: "Até (opcional)",
  venue: "Local (opcional, ex.: DAVIarena)",
  submit: "Verificar e adicionar",
  checking: "Verificando na web…",
  limit: "Você pode informar até 3 eventos por dia.",
  close: "Fechar",
  exists: "Já estava na lista",
  verified: "Confirmado",
  unverified: "Não confirmado",
};

const catalog = { es, en, pt };
export default catalog;
