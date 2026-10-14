// Modo sin conexión (feature 029). El español es la referencia: en/pt con las MISMAS claves.
const es = {
  badge: "Sin conexión",
  gate: {
    title: "¿Cómo quieres empezar?",
    connectTitle: "Conectar mi channel manager",
    connectText: "Si usas Beds24, StayLever importa tu apartamento y publica los precios que apruebes.",
    connectCta: "Ir a Ajustes",
    manualTitle: "Usar sin conexión",
    manualText:
      "Crea tu apartamento a mano en 2 minutos. StayLever te sugiere precios con eventos y " +
      "temporadas, y tú los copias en Airbnb y Booking. Gratis y sin configuración técnica.",
    manualCta: "Crear mi apartamento",
  },
  setup: {
    title: "Tu apartamento",
    description:
      "Con estos datos StayLever arma tu calendario de precios. Podrás cambiarlos cuando quieras.",
    name: "Nombre del apartamento",
    city: "Ciudad",
    currency: "Moneda",
    weekday: "Precio por noche entre semana",
    weekend: "Precio por noche de viernes y sábado (opcional)",
    listings: "Tus anuncios (opcional)",
    listingsHint:
      "El enlace del anuncio sirve para abrir tu calendario rápido. El enlace iCal de exportación " +
      "le dice a StayLever qué noches ya están ocupadas, para no sugerir precios en ellas.",
    airbnbUrl: "Enlace de tu anuncio en Airbnb",
    airbnbIcal: "Enlace iCal de exportación de Airbnb",
    bookingUrl: "Enlace de tu anuncio en Booking",
    bookingIcal: "Enlace iCal de exportación de Booking",
    icalHelp:
      "Airbnb: Calendario → Disponibilidad → Conectar calendarios → Exportar calendario. " +
      "Booking: Extranet → Tarifas y disponibilidad → Sincronizar calendarios → Exportar.",
    submit: "Crear apartamento",
    creating: "Creando…",
    created: "Apartamento creado. Tus sugerencias llegan con el próximo escaneo diario.",
  },
  card: {
    title: "Modo sin conexión",
    description:
      "StayLever guarda tus precios y ocupación, pero no publica nada: aplica los cambios a mano " +
      "en cada plataforma con estos enlaces.",
    openCalendar: (channel: string) => `Abrir calendario de ${channel}`,
    openListing: "Ver anuncio",
    ical: "Calendario iCal",
    icalOn: "conectado",
    icalOff: "sin conectar",
    edit: "Editar enlaces",
    save: "Guardar enlaces",
    saved: "Enlaces guardados",
    sync: "Sincronizar calendarios ahora",
    syncing: "Sincronizando…",
    synced: (b: number, c: number) => `Listo: ${b} reserva(s) nuevas, ${c} cancelada(s).`,
    syncErrors: (e: string) => `Algunos calendarios fallaron: ${e}`,
    addAnother: "Agregar otro apartamento",
  },
  banner:
    "Estás sin conexión: al aplicar, StayLever guarda el precio y tú lo copias en cada plataforma.",
};

type Shape = typeof es;

const en: Shape = {
  badge: "Offline",
  gate: {
    title: "How do you want to start?",
    connectTitle: "Connect my channel manager",
    connectText: "If you use Beds24, StayLever imports your apartment and publishes the prices you approve.",
    connectCta: "Go to Settings",
    manualTitle: "Use it offline",
    manualText:
      "Create your apartment by hand in 2 minutes. StayLever suggests prices from events and " +
      "seasons, and you copy them to Airbnb and Booking. Free, no technical setup.",
    manualCta: "Create my apartment",
  },
  setup: {
    title: "Your apartment",
    description: "StayLever builds your price calendar from this. You can change it anytime.",
    name: "Apartment name",
    city: "City",
    currency: "Currency",
    weekday: "Price per weeknight",
    weekend: "Price per Friday and Saturday night (optional)",
    listings: "Your listings (optional)",
    listingsHint:
      "The listing link opens your calendar quickly. The export iCal link tells StayLever which " +
      "nights are already booked, so it doesn't suggest prices for them.",
    airbnbUrl: "Your Airbnb listing link",
    airbnbIcal: "Airbnb export iCal link",
    bookingUrl: "Your Booking listing link",
    bookingIcal: "Booking export iCal link",
    icalHelp:
      "Airbnb: Calendar → Availability → Connect calendars → Export calendar. " +
      "Booking: Extranet → Rates & availability → Sync calendars → Export.",
    submit: "Create apartment",
    creating: "Creating…",
    created: "Apartment created. Your suggestions arrive with the next daily scan.",
  },
  card: {
    title: "Offline mode",
    description:
      "StayLever keeps your prices and occupancy but publishes nothing: apply changes by hand on " +
      "each platform with these links.",
    openCalendar: (channel) => `Open ${channel} calendar`,
    openListing: "View listing",
    ical: "iCal calendar",
    icalOn: "connected",
    icalOff: "not connected",
    edit: "Edit links",
    save: "Save links",
    saved: "Links saved",
    sync: "Sync calendars now",
    syncing: "Syncing…",
    synced: (b, c) => `Done: ${b} new booking(s), ${c} cancelled.`,
    syncErrors: (e) => `Some calendars failed: ${e}`,
    addAnother: "Add another apartment",
  },
  banner: "You're offline: when you apply, StayLever saves the price and you copy it to each platform.",
};

const pt: Shape = {
  badge: "Sem conexão",
  gate: {
    title: "Como você quer começar?",
    connectTitle: "Conectar meu channel manager",
    connectText: "Se você usa o Beds24, o StayLever importa seu apartamento e publica os preços que você aprovar.",
    connectCta: "Ir para Ajustes",
    manualTitle: "Usar sem conexão",
    manualText:
      "Crie seu apartamento à mão em 2 minutos. O StayLever sugere preços com eventos e " +
      "temporadas, e você os copia no Airbnb e no Booking. Grátis e sem configuração técnica.",
    manualCta: "Criar meu apartamento",
  },
  setup: {
    title: "Seu apartamento",
    description: "Com esses dados o StayLever monta seu calendário de preços. Você pode mudar quando quiser.",
    name: "Nome do apartamento",
    city: "Cidade",
    currency: "Moeda",
    weekday: "Preço por noite durante a semana",
    weekend: "Preço por noite de sexta e sábado (opcional)",
    listings: "Seus anúncios (opcional)",
    listingsHint:
      "O link do anúncio abre seu calendário rápido. O link iCal de exportação diz ao StayLever " +
      "quais noites já estão ocupadas, para não sugerir preços nelas.",
    airbnbUrl: "Link do seu anúncio no Airbnb",
    airbnbIcal: "Link iCal de exportação do Airbnb",
    bookingUrl: "Link do seu anúncio no Booking",
    bookingIcal: "Link iCal de exportação do Booking",
    icalHelp:
      "Airbnb: Calendário → Disponibilidade → Conectar calendários → Exportar calendário. " +
      "Booking: Extranet → Tarifas e disponibilidade → Sincronizar calendários → Exportar.",
    submit: "Criar apartamento",
    creating: "Criando…",
    created: "Apartamento criado. Suas sugestões chegam com a próxima varredura diária.",
  },
  card: {
    title: "Modo sem conexão",
    description:
      "O StayLever guarda seus preços e a ocupação, mas não publica nada: aplique as mudanças à " +
      "mão em cada plataforma com estes links.",
    openCalendar: (channel) => `Abrir calendário do ${channel}`,
    openListing: "Ver anúncio",
    ical: "Calendário iCal",
    icalOn: "conectado",
    icalOff: "não conectado",
    edit: "Editar links",
    save: "Salvar links",
    saved: "Links salvos",
    sync: "Sincronizar calendários agora",
    syncing: "Sincronizando…",
    synced: (b, c) => `Pronto: ${b} reserva(s) nova(s), ${c} cancelada(s).`,
    syncErrors: (e) => `Alguns calendários falharam: ${e}`,
    addAnother: "Adicionar outro apartamento",
  },
  banner: "Você está sem conexão: ao aplicar, o StayLever guarda o preço e você o copia em cada plataforma.",
};

const catalog = { es, en, pt };
export default catalog;
